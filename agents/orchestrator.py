"""
BiblioAgent AI - SLR Orchestrator
=================================
LangGraph-based state machine for orchestrating the multi-agent
Systematic Literature Review workflow.
"""

import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import SLRState, AgentStatus, create_initial_state
from .search_agent import search_node
from .screening_agent import screening_node
from .scrounger_agent import acquisition_node
from .quality_agent import quality_node

logger = logging.getLogger(__name__)


class SLROrchestrator:
    """
    Orchestrates the SLR workflow using LangGraph state machine.

    Workflow:
    1. Search Agent: Generate queries and search Scopus
    2. Screening Agent: Title and abstract screening
    3. Scrounger Agent: Full-text acquisition
    4. Quality Agent: JBI quality assessment

    The orchestrator handles:
    - State transitions between agents
    - Error handling and recovery
    - Progress callbacks for UI updates
    - Checkpointing for resumable workflows
    """

    def __init__(
        self,
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
        enable_checkpointing: bool = False  # Disabled by default due to numpy serialization issues
    ):
        """
        Initialize the SLR Orchestrator.

        Args:
            progress_callback: Optional callback(phase, percent, message) for UI updates
            enable_checkpointing: Whether to enable workflow checkpointing
        """
        self.progress_callback = progress_callback
        self.checkpointer = MemorySaver() if enable_checkpointing else None
        self.graph = self._build_graph()
        self.current_state = None

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow graph."""

        # Create the state graph
        workflow = StateGraph(SLRState)

        # Add nodes for each agent
        workflow.add_node("search", self._wrap_node(search_node, "search"))
        workflow.add_node("screening", self._wrap_node(screening_node, "screening"))
        workflow.add_node("acquisition", self._wrap_node(acquisition_node, "acquisition"))
        workflow.add_node("quality", self._wrap_node(quality_node, "quality"))

        # Define edges (linear workflow)
        workflow.set_entry_point("search")
        workflow.add_edge("search", "screening")
        workflow.add_edge("screening", "acquisition")
        workflow.add_edge("acquisition", "quality")
        workflow.add_edge("quality", END)

        # Add conditional edges for error handling
        workflow.add_conditional_edges(
            "search",
            self._check_for_errors,
            {
                "continue": "screening",
                "error": END,
            }
        )
        workflow.add_conditional_edges(
            "screening",
            self._check_for_errors,
            {
                "continue": "acquisition",
                "error": END,
            }
        )
        workflow.add_conditional_edges(
            "acquisition",
            self._check_for_errors,
            {
                "continue": "quality",
                "error": END,
            }
        )

        return workflow.compile(checkpointer=self.checkpointer)

    def _wrap_node(
        self,
        node_func: Callable,
        phase_name: str
    ) -> Callable:
        """Wrap a node function with progress reporting and error handling."""

        async def wrapped(state: SLRState) -> SLRState:
            # Report phase start
            if self.progress_callback:
                phase_progress = {
                    "search": 0,
                    "screening": 25,
                    "acquisition": 50,
                    "quality": 75,
                }
                self.progress_callback(
                    phase_name,
                    phase_progress.get(phase_name, 0),
                    f"Starting {phase_name} phase..."
                )

            try:
                # Execute the actual node
                result = await node_func(state)

                # Report phase completion
                if self.progress_callback:
                    completion_progress = {
                        "search": 25,
                        "screening": 50,
                        "acquisition": 75,
                        "quality": 100,
                    }
                    self.progress_callback(
                        phase_name,
                        completion_progress.get(phase_name, 100),
                        f"Completed {phase_name} phase"
                    )

                return result

            except Exception as e:
                logger.error(f"Error in {phase_name} phase: {e}")
                state["errors"].append(f"{phase_name} error: {str(e)}")
                state["agent_status"][phase_name] = AgentStatus.ERROR.value

                if self.progress_callback:
                    self.progress_callback(
                        phase_name,
                        -1,  # Negative indicates error
                        f"Error in {phase_name}: {str(e)}"
                    )

                return state

        return wrapped

    def _check_for_errors(self, state: SLRState) -> str:
        """Check if the workflow should continue or stop due to errors."""
        for agent_name, status in state["agent_status"].items():
            if status == AgentStatus.ERROR.value:
                return "error"
        return "continue"

    async def run(
        self,
        research_question: str,
        inclusion_criteria: List[str],
        exclusion_criteria: List[str],
        date_range: tuple = (2018, 2025),
        languages: List[str] = None,
        thread_id: str = None
    ) -> SLRState:
        """
        Run the complete SLR workflow.

        Args:
            research_question: The research question to investigate
            inclusion_criteria: List of inclusion criteria
            exclusion_criteria: List of exclusion criteria
            date_range: (start_year, end_year) tuple
            languages: List of acceptable languages
            thread_id: Optional thread ID for checkpointing

        Returns:
            Final SLRState with all results
        """
        # Create initial state
        initial_state = create_initial_state(
            research_question=research_question,
            inclusion_criteria=inclusion_criteria,
            exclusion_criteria=exclusion_criteria,
            date_range=date_range,
            languages=languages or ["en"]
        )

        config = {}
        if self.checkpointer:
            # Always provide thread_id when checkpointing is enabled
            import uuid
            actual_thread_id = thread_id or f"slr_{uuid.uuid4().hex[:8]}"
            config["configurable"] = {"thread_id": actual_thread_id}

        # Run the workflow
        logger.info(f"Starting SLR workflow for: {research_question[:100]}...")

        try:
            final_state = await self.graph.ainvoke(initial_state, config)
            self.current_state = final_state

            logger.info(
                f"SLR workflow completed. "
                f"Identified: {final_state['prisma_stats']['identified']}, "
                f"Included: {final_state['prisma_stats']['included_synthesis']}"
            )

            return final_state

        except Exception as e:
            logger.error(f"SLR workflow failed: {e}")
            initial_state["errors"].append(f"Workflow error: {str(e)}")
            return initial_state

    async def resume(self, thread_id: str) -> Optional[SLRState]:
        """
        Resume a previously checkpointed workflow.

        Args:
            thread_id: The thread ID of the workflow to resume

        Returns:
            Final state after resuming, or None if thread not found
        """
        if not self.checkpointer:
            logger.warning("Checkpointing not enabled, cannot resume")
            return None

        config = {"configurable": {"thread_id": thread_id}}

        try:
            # Get the last state from the checkpoint
            state = await self.graph.aget_state(config)

            if state and state.values:
                logger.info(f"Resuming workflow from thread {thread_id}")
                final_state = await self.graph.ainvoke(None, config)
                self.current_state = final_state
                return final_state
            else:
                logger.warning(f"No checkpoint found for thread {thread_id}")
                return None

        except Exception as e:
            logger.error(f"Failed to resume workflow: {e}")
            return None

    def get_prisma_stats(self) -> Dict[str, int]:
        """Get current PRISMA statistics."""
        if self.current_state:
            return self.current_state.get("prisma_stats", {})
        return {}

    def get_processing_log(self) -> List[str]:
        """Get the processing log."""
        if self.current_state:
            return self.current_state.get("processing_log", [])
        return []

    def get_errors(self) -> List[str]:
        """Get any errors that occurred."""
        if self.current_state:
            return self.current_state.get("errors", [])
        return []


# Convenience function for quick execution
async def run_slr_pipeline(
    research_question: str,
    inclusion_criteria: List[str],
    exclusion_criteria: List[str],
    date_range: tuple = (2018, 2025),
    progress_callback: Optional[Callable] = None
) -> SLRState:
    """
    Convenience function to run the full SLR pipeline.

    Args:
        research_question: The research question
        inclusion_criteria: List of inclusion criteria
        exclusion_criteria: List of exclusion criteria
        date_range: (start_year, end_year) tuple
        progress_callback: Optional progress callback

    Returns:
        Final SLRState with results
    """
    orchestrator = SLROrchestrator(progress_callback=progress_callback)
    return await orchestrator.run(
        research_question=research_question,
        inclusion_criteria=inclusion_criteria,
        exclusion_criteria=exclusion_criteria,
        date_range=date_range
    )

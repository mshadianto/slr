"""
Muezza AI - Faithful Research Companion
=======================================
Premium Agentic Systematic Literature Review Dashboard.
Enterprise-grade UI with modern, serene aesthetics.

Developer: MS Hadianto
Usage:
    streamlit run app.py
"""

import streamlit as st

# ============================================================================
# APPLICATION METADATA
# ============================================================================
__version__ = "2.2.0"
__author__ = "MS Hadianto"
__app_name__ = "Muezza AI"
__tagline__ = "Faithful Research Companion"
__release_date__ = "2026-01-24"

APP_INFO = {
    "name": __app_name__,
    "version": __version__,
    "author": __author__,
    "tagline": __tagline__,
    "release_date": __release_date__,
    "github": "https://github.com/mshadianto/slr",
    "description": "Intelligent Systematic Literature Review Automation System"
}
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import asyncio
import nest_asyncio
try:
    nest_asyncio.apply()  # Allow nested event loops for Streamlit compatibility
except ValueError:
    pass  # uvloop doesn't need patching and is incompatible with nest_asyncio
import time
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import local modules
from config import settings
from agents.state import SLRState, PRISMAStats, AgentStatus, create_initial_state
from agents.orchestrator import SLROrchestrator
from agents.narrative_generator import NarrativeGenerator, generate_results_chapter
from agents.narrative_orchestrator import NarrativeOrchestrator
from agents.citation_stitcher import CitationAutoStitcher, CitationStyle
from agents.logic_continuity_agent import LogicContinuityAgent
from agents.forensic_audit_agent import ForensicAuditAgent, VerificationStatus
from agents.docx_generator import DocxGenerator

# Page configuration
st.set_page_config(
    page_title="Muezza AI | Faithful Research Companion",
    page_icon="🐱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# EXECUTIVE PRO CSS THEME - Ultra Premium Glassmorphism Design
# ============================================================================
st.markdown("""
<style>
    /* ===== GOOGLE FONTS ===== */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap');

    /* ===== ROOT VARIABLES ===== */
    :root {
        --emerald-50: #ecfdf5;
        --emerald-100: #d1fae5;
        --emerald-200: #a7f3d0;
        --emerald-300: #6ee7b7;
        --emerald-400: #34d399;
        --emerald-500: #10b981;
        --emerald-600: #059669;
        --emerald-700: #047857;
        --emerald-800: #065f46;
        --emerald-900: #064e3b;

        --gold-50: #fffbeb;
        --gold-100: #fef3c7;
        --gold-200: #fde68a;
        --gold-300: #fcd34d;
        --gold-400: #fbbf24;
        --gold-500: #f59e0b;
        --gold-600: #d97706;
        --gold-700: #b45309;

        --slate-50: #f8fafc;
        --slate-100: #f1f5f9;
        --slate-200: #e2e8f0;
        --slate-300: #cbd5e1;
        --slate-400: #94a3b8;
        --slate-500: #64748b;
        --slate-600: #475569;
        --slate-700: #334155;
        --slate-800: #1e293b;
        --slate-900: #0f172a;
        --slate-950: #020617;

        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
        --info: #3b82f6;
        --purple: #8b5cf6;
        --cyan: #06b6d4;

        /* Premium Glass Variables */
        --glass-bg: rgba(15, 23, 42, 0.6);
        --glass-bg-light: rgba(30, 41, 59, 0.5);
        --glass-border: rgba(148, 163, 184, 0.08);
        --glass-border-light: rgba(255, 255, 255, 0.05);
        --glass-shine: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, transparent 50%);

        /* Premium Shadows */
        --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.3);
        --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.4);
        --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.5);
        --shadow-xl: 0 16px 48px rgba(0, 0, 0, 0.6);
        --shadow-glow-emerald: 0 0 40px rgba(16, 185, 129, 0.2), 0 0 80px rgba(16, 185, 129, 0.1);
        --shadow-glow-gold: 0 0 40px rgba(245, 158, 11, 0.2), 0 0 80px rgba(245, 158, 11, 0.1);
    }

    /* ===== GLOBAL STYLES ===== */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    .stApp {
        background:
            radial-gradient(ellipse 80% 50% at 20% 10%, rgba(16, 185, 129, 0.12) 0%, transparent 50%),
            radial-gradient(ellipse 60% 40% at 80% 90%, rgba(245, 158, 11, 0.08) 0%, transparent 50%),
            radial-gradient(ellipse 50% 30% at 50% 50%, rgba(139, 92, 246, 0.05) 0%, transparent 50%),
            linear-gradient(180deg, #020617 0%, #0f172a 30%, #1e293b 70%, #0f172a 100%);
        min-height: 100vh;
        position: relative;
    }

    /* Animated background mesh */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-image:
            linear-gradient(rgba(16, 185, 129, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(16, 185, 129, 0.03) 1px, transparent 1px);
        background-size: 50px 50px;
        pointer-events: none;
        z-index: 0;
        animation: meshMove 20s linear infinite;
    }

    @keyframes meshMove {
        0% { background-position: 0 0; }
        100% { background-position: 50px 50px; }
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ===== SIDEBAR STYLES ===== */
    [data-testid="stSidebar"] {
        background:
            linear-gradient(180deg,
                rgba(2, 6, 23, 0.98) 0%,
                rgba(15, 23, 42, 0.95) 50%,
                rgba(2, 6, 23, 0.98) 100%);
        border-right: 1px solid rgba(16, 185, 129, 0.15);
        backdrop-filter: blur(24px) saturate(180%);
        box-shadow:
            4px 0 24px rgba(0, 0, 0, 0.5),
            inset -1px 0 0 rgba(255, 255, 255, 0.02);
    }

    [data-testid="stSidebar"]::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 300px;
        background:
            radial-gradient(ellipse 100% 100% at 50% 0%, rgba(16, 185, 129, 0.15) 0%, transparent 70%);
        pointer-events: none;
        z-index: 0;
    }

    [data-testid="stSidebar"]::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 200px;
        background:
            radial-gradient(ellipse 100% 100% at 50% 100%, rgba(245, 158, 11, 0.08) 0%, transparent 70%);
        pointer-events: none;
        z-index: 0;
    }

    [data-testid="stSidebar"] .stMarkdown {
        color: var(--slate-200);
        position: relative;
        z-index: 1;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: var(--emerald-400) !important;
        font-weight: 700;
        font-family: 'Space Grotesk', sans-serif;
        text-shadow: 0 0 40px rgba(16, 185, 129, 0.4);
        letter-spacing: -0.02em;
    }

    [data-testid="stSidebar"] .stTextInput label,
    [data-testid="stSidebar"] .stTextArea label,
    [data-testid="stSidebar"] .stSelectbox label {
        color: var(--slate-300) !important;
        font-weight: 500;
        font-size: 0.875rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* ===== MAIN HEADER ===== */
    .main-header {
        background:
            linear-gradient(135deg,
                rgba(6, 78, 59, 0.5) 0%,
                rgba(15, 23, 42, 0.7) 30%,
                rgba(30, 41, 59, 0.6) 70%,
                rgba(6, 95, 70, 0.4) 100%);
        padding: 3rem 3.5rem;
        border-radius: 28px;
        margin-bottom: 2.5rem;
        border: 1px solid rgba(16, 185, 129, 0.2);
        box-shadow:
            0 8px 40px rgba(0, 0, 0, 0.5),
            0 0 80px rgba(16, 185, 129, 0.08),
            0 0 120px rgba(245, 158, 11, 0.05),
            inset 0 1px 0 rgba(255, 255, 255, 0.06),
            inset 0 -1px 0 rgba(0, 0, 0, 0.2);
        position: relative;
        overflow: hidden;
        backdrop-filter: blur(24px) saturate(180%);
    }

    .main-header::before {
        content: '';
        position: absolute;
        top: -100%;
        right: -30%;
        width: 600px;
        height: 600px;
        background: radial-gradient(circle, rgba(245, 158, 11, 0.12) 0%, transparent 60%);
        pointer-events: none;
        animation: headerOrb 15s ease-in-out infinite alternate;
    }

    @keyframes headerOrb {
        0% { transform: translate(0, 0) scale(1); }
        100% { transform: translate(-50px, 50px) scale(1.2); }
    }

    .main-header::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 5%;
        right: 5%;
        height: 1px;
        background: linear-gradient(90deg,
            transparent,
            rgba(16, 185, 129, 0.4) 20%,
            rgba(245, 158, 11, 0.3) 50%,
            rgba(16, 185, 129, 0.4) 80%,
            transparent);
    }

    .main-header h1 {
        margin: 0;
        font-size: 3.25rem;
        font-weight: 900;
        font-family: 'Space Grotesk', sans-serif;
        background: linear-gradient(135deg,
            #6ee7b7 0%,
            #34d399 20%,
            #10b981 40%,
            #fbbf24 60%,
            #f59e0b 80%,
            #fcd34d 100%);
        background-size: 200% 200%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: gradientShift 8s ease-in-out infinite;
        letter-spacing: -0.03em;
        position: relative;
    }

    @keyframes gradientShift {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }

    .main-header .tagline {
        margin: 1rem 0 0 0;
        font-size: 1.15rem;
        color: var(--slate-300);
        font-weight: 400;
        letter-spacing: 0.5px;
        opacity: 0.85;
        position: relative;
    }

    .main-header .version-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        background: linear-gradient(135deg, var(--gold-400), var(--gold-600));
        color: var(--slate-900);
        padding: 0.4rem 1.1rem;
        border-radius: 24px;
        font-size: 0.7rem;
        font-weight: 800;
        margin-left: 1.25rem;
        vertical-align: middle;
        box-shadow:
            0 2px 12px rgba(245, 158, 11, 0.4),
            inset 0 1px 0 rgba(255, 255, 255, 0.3);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        position: relative;
        overflow: hidden;
    }

    .main-header .version-badge::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
        animation: badgeShine 3s ease-in-out infinite;
    }

    @keyframes badgeShine {
        0%, 100% { left: -100%; }
        50% { left: 100%; }
    }

    /* ===== AGENT CARDS ===== */
    .agent-card {
        background:
            linear-gradient(145deg,
                rgba(30, 41, 59, 0.7) 0%,
                rgba(15, 23, 42, 0.85) 100%);
        border-radius: 20px;
        padding: 1.75rem;
        margin: 0.75rem 0;
        border: 1px solid rgba(148, 163, 184, 0.08);
        transition: all 0.5s cubic-bezier(0.23, 1, 0.32, 1);
        position: relative;
        overflow: hidden;
        backdrop-filter: blur(16px) saturate(180%);
        box-shadow:
            0 4px 24px rgba(0, 0, 0, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.04);
    }

    .agent-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent 10%, rgba(255,255,255,0.08) 50%, transparent 90%);
    }

    .agent-card::after {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle at center, rgba(16, 185, 129, 0.03) 0%, transparent 50%);
        opacity: 0;
        transition: opacity 0.5s ease;
        pointer-events: none;
    }

    .agent-card:hover {
        transform: translateY(-6px) scale(1.02);
        box-shadow:
            0 24px 48px rgba(0, 0, 0, 0.5),
            0 0 40px rgba(16, 185, 129, 0.08),
            inset 0 1px 0 rgba(255, 255, 255, 0.06);
        border-color: rgba(16, 185, 129, 0.25);
    }

    .agent-card:hover::after {
        opacity: 1;
    }

    .agent-card.active {
        border-color: rgba(16, 185, 129, 0.5);
        background:
            linear-gradient(145deg,
                rgba(6, 78, 59, 0.4) 0%,
                rgba(15, 23, 42, 0.85) 100%);
        box-shadow:
            0 8px 32px rgba(0, 0, 0, 0.4),
            0 0 60px rgba(16, 185, 129, 0.15),
            inset 0 0 40px rgba(16, 185, 129, 0.03);
        animation: activeCardGlow 3s ease-in-out infinite;
    }

    @keyframes activeCardGlow {
        0%, 100% {
            box-shadow:
                0 8px 32px rgba(0, 0, 0, 0.4),
                0 0 40px rgba(16, 185, 129, 0.15);
        }
        50% {
            box-shadow:
                0 8px 32px rgba(0, 0, 0, 0.4),
                0 0 80px rgba(16, 185, 129, 0.25);
        }
    }

    .agent-card.active .agent-indicator {
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: linear-gradient(180deg, var(--emerald-300), var(--emerald-500), var(--emerald-700));
        box-shadow: 0 0 24px var(--emerald-500);
        border-radius: 0 4px 4px 0;
    }

    .agent-card.completed {
        border-color: rgba(245, 158, 11, 0.4);
        background:
            linear-gradient(145deg,
                rgba(45, 39, 28, 0.4) 0%,
                rgba(15, 23, 42, 0.85) 100%);
    }

    .agent-card.completed .agent-indicator {
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: linear-gradient(180deg, var(--gold-300), var(--gold-500), var(--gold-700));
        box-shadow: 0 0 20px var(--gold-500);
        border-radius: 0 4px 4px 0;
    }

    .agent-card.error {
        border-color: rgba(239, 68, 68, 0.4);
        box-shadow:
            0 4px 24px rgba(0, 0, 0, 0.3),
            0 0 30px rgba(239, 68, 68, 0.1);
    }

    .agent-card .agent-icon {
        font-size: 2.25rem;
        margin-bottom: 1rem;
        filter: drop-shadow(0 4px 12px rgba(255,255,255,0.15));
        transition: transform 0.3s ease;
    }

    .agent-card:hover .agent-icon {
        transform: scale(1.1);
    }

    .agent-card .agent-name {
        font-size: 1.05rem;
        font-weight: 700;
        font-family: 'Space Grotesk', sans-serif;
        color: var(--slate-100);
        margin: 0;
        letter-spacing: -0.01em;
    }

    .agent-card .agent-status {
        font-size: 0.8rem;
        color: var(--slate-400);
        margin-top: 0.6rem;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .agent-card .agent-status.running {
        color: var(--emerald-400);
        text-shadow: 0 0 12px rgba(16, 185, 129, 0.6);
    }

    .agent-card .agent-status.running::before {
        content: '';
        width: 8px;
        height: 8px;
        background: var(--emerald-400);
        border-radius: 50%;
        animation: statusPulse 1.5s ease-in-out infinite;
        box-shadow: 0 0 12px var(--emerald-400);
    }

    @keyframes statusPulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(0.8); }
    }

    .agent-card .agent-status.completed {
        color: var(--gold-400);
        text-shadow: 0 0 12px rgba(245, 158, 11, 0.6);
    }

    .agent-card .agent-status.completed::before {
        content: '✓';
        font-size: 0.75rem;
        font-weight: 700;
    }

    /* ===== API STATUS INDICATORS ===== */
    .api-status {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem 1rem;
        background:
            linear-gradient(135deg,
                rgba(30, 41, 59, 0.6) 0%,
                rgba(15, 23, 42, 0.8) 100%);
        border-radius: 12px;
        margin: 0.35rem 0;
        border: 1px solid rgba(148, 163, 184, 0.08);
        backdrop-filter: blur(8px);
        transition: all 0.3s ease;
    }

    .api-status:hover {
        border-color: rgba(148, 163, 184, 0.15);
        transform: translateX(4px);
    }

    .api-status .dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        position: relative;
    }

    .api-status .dot::after {
        content: '';
        position: absolute;
        top: -3px;
        left: -3px;
        right: -3px;
        bottom: -3px;
        border-radius: 50%;
        animation: dotRing 2s ease-in-out infinite;
    }

    .api-status .dot.online {
        background: var(--emerald-400);
        box-shadow: 0 0 12px var(--emerald-500);
    }

    .api-status .dot.online::after {
        border: 2px solid var(--emerald-400);
        opacity: 0.3;
    }

    .api-status .dot.offline {
        background: var(--danger);
        box-shadow: 0 0 8px var(--danger);
    }

    .api-status .dot.offline::after {
        display: none;
    }

    .api-status .dot.warning {
        background: var(--warning);
        box-shadow: 0 0 8px var(--warning);
    }

    @keyframes dotRing {
        0%, 100% { transform: scale(1); opacity: 0.3; }
        50% { transform: scale(1.4); opacity: 0; }
    }

    .api-status .name {
        font-size: 0.85rem;
        color: var(--slate-300);
        font-weight: 500;
        flex: 1;
    }

    .api-status .status-label {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 0.25rem 0.6rem;
        border-radius: 6px;
        font-weight: 600;
    }

    .api-status .status-label.online {
        background: rgba(16, 185, 129, 0.15);
        color: var(--emerald-400);
    }

    .api-status .status-label.offline {
        background: rgba(239, 68, 68, 0.15);
        color: var(--danger);
    }

    /* ===== PRISMA METRICS ===== */
    .metric-card {
        background:
            linear-gradient(145deg,
                rgba(30, 41, 59, 0.65) 0%,
                rgba(15, 23, 42, 0.85) 100%);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        border: 1px solid rgba(148, 163, 184, 0.08);
        transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1);
        position: relative;
        overflow: hidden;
        backdrop-filter: blur(12px);
    }

    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent);
    }

    .metric-card:hover {
        border-color: rgba(16, 185, 129, 0.3);
        transform: translateY(-4px);
        box-shadow:
            0 16px 32px rgba(0, 0, 0, 0.4),
            0 0 40px rgba(16, 185, 129, 0.08);
    }

    .metric-card .number {
        font-size: 2.75rem;
        font-weight: 800;
        font-family: 'Space Grotesk', sans-serif;
        background: linear-gradient(135deg, var(--emerald-300), var(--emerald-500), var(--gold-400));
        background-size: 200% 200%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: metricGradient 4s ease-in-out infinite;
        line-height: 1;
    }

    @keyframes metricGradient {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }

    .metric-card .label {
        font-size: 0.8rem;
        color: var(--slate-400);
        margin-top: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 600;
    }

    .metric-card .delta {
        font-size: 0.75rem;
        margin-top: 0.5rem;
        padding: 0.2rem 0.5rem;
        border-radius: 8px;
        display: inline-block;
    }

    .metric-card .delta.positive {
        background: rgba(16, 185, 129, 0.15);
        color: var(--emerald-400);
    }

    .metric-card .delta.negative {
        background: rgba(239, 68, 68, 0.15);
        color: var(--danger);
    }

    /* ===== TERMINAL LOG ===== */
    .terminal-log {
        background:
            linear-gradient(180deg,
                rgba(2, 6, 23, 0.95) 0%,
                rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(148, 163, 184, 0.1);
        border-radius: 16px;
        padding: 1.25rem;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.82rem;
        max-height: 350px;
        overflow-y: auto;
        position: relative;
        box-shadow:
            inset 0 2px 20px rgba(0, 0, 0, 0.3),
            0 4px 24px rgba(0, 0, 0, 0.3);
    }

    .terminal-log::before {
        content: '● ● ●';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        padding: 0.5rem 1rem;
        font-size: 0.6rem;
        letter-spacing: 4px;
        color: var(--slate-600);
        background: rgba(15, 23, 42, 0.8);
        border-bottom: 1px solid rgba(148, 163, 184, 0.08);
        border-radius: 16px 16px 0 0;
    }

    .terminal-log .log-content {
        margin-top: 1.5rem;
    }

    .terminal-log .log-entry {
        padding: 0.4rem 0;
        border-bottom: 1px solid rgba(148, 163, 184, 0.05);
        color: var(--slate-300);
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
        transition: background 0.2s ease;
    }

    .terminal-log .log-entry:hover {
        background: rgba(16, 185, 129, 0.03);
    }

    .terminal-log .log-entry:last-child {
        border-bottom: none;
    }

    .terminal-log .timestamp {
        color: var(--slate-500);
        font-size: 0.75rem;
        min-width: 70px;
        font-weight: 500;
    }

    .terminal-log .agent-name {
        color: var(--emerald-400);
        font-weight: 600;
        text-shadow: 0 0 8px rgba(16, 185, 129, 0.3);
    }

    .terminal-log .action {
        color: var(--gold-400);
    }

    .terminal-log .success {
        color: var(--emerald-400);
    }

    .terminal-log .error {
        color: var(--danger);
        text-shadow: 0 0 8px rgba(239, 68, 68, 0.3);
    }

    .terminal-log .cursor {
        display: inline-block;
        width: 8px;
        height: 14px;
        background: var(--emerald-400);
        animation: cursorBlink 1s step-end infinite;
        margin-left: 4px;
        vertical-align: middle;
    }

    @keyframes cursorBlink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0; }
    }

    /* ===== DATA TABLE ===== */
    .audit-table {
        background:
            linear-gradient(145deg,
                rgba(30, 41, 59, 0.6) 0%,
                rgba(15, 23, 42, 0.8) 100%);
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid rgba(148, 163, 184, 0.08);
        backdrop-filter: blur(12px);
    }

    .audit-table th {
        background: rgba(2, 6, 23, 0.8);
        color: var(--emerald-400);
        padding: 1.1rem 1.25rem;
        text-transform: uppercase;
        font-size: 0.7rem;
        letter-spacing: 0.1em;
        font-weight: 700;
        border-bottom: 1px solid rgba(16, 185, 129, 0.2);
    }

    .audit-table td {
        padding: 1rem 1.25rem;
        color: var(--slate-200);
        border-bottom: 1px solid rgba(148, 163, 184, 0.05);
        transition: all 0.2s ease;
    }

    .audit-table tr:hover td {
        background: rgba(16, 185, 129, 0.05);
    }

    /* ===== BUTTONS ===== */
    .stButton > button {
        background:
            linear-gradient(135deg, var(--emerald-500), var(--emerald-700)) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.65rem 1.75rem !important;
        font-weight: 700 !important;
        font-family: 'Inter', sans-serif !important;
        letter-spacing: 0.02em !important;
        transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1) !important;
        box-shadow:
            0 4px 16px rgba(16, 185, 129, 0.35),
            inset 0 1px 0 rgba(255, 255, 255, 0.15) !important;
        position: relative !important;
        overflow: hidden !important;
    }

    .stButton > button::before {
        content: '' !important;
        position: absolute !important;
        top: 0 !important;
        left: -100% !important;
        width: 100% !important;
        height: 100% !important;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent) !important;
        transition: left 0.5s ease !important;
    }

    .stButton > button:hover::before {
        left: 100% !important;
    }

    .stButton > button:hover {
        transform: translateY(-3px) scale(1.02) !important;
        box-shadow:
            0 8px 28px rgba(16, 185, 129, 0.45),
            inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
    }

    .stButton > button:active {
        transform: translateY(-1px) scale(0.98) !important;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--gold-400), var(--gold-600)) !important;
        box-shadow:
            0 4px 16px rgba(245, 158, 11, 0.35),
            inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
    }

    .stButton > button[kind="primary"]:hover {
        box-shadow:
            0 8px 28px rgba(245, 158, 11, 0.45),
            inset 0 1px 0 rgba(255, 255, 255, 0.25) !important;
    }

    /* Secondary/Ghost button style */
    .stButton > button[kind="secondary"] {
        background: transparent !important;
        border: 2px solid rgba(16, 185, 129, 0.4) !important;
        color: var(--emerald-400) !important;
        box-shadow: none !important;
    }

    .stButton > button[kind="secondary"]:hover {
        background: rgba(16, 185, 129, 0.1) !important;
        border-color: var(--emerald-400) !important;
        box-shadow: 0 0 20px rgba(16, 185, 129, 0.2) !important;
    }

    /* ===== TABS ===== */
    .stTabs [data-baseweb="tab-list"] {
        background:
            linear-gradient(145deg,
                rgba(30, 41, 59, 0.6) 0%,
                rgba(15, 23, 42, 0.8) 100%);
        border-radius: 16px;
        padding: 0.5rem;
        gap: 0.5rem;
        border: 1px solid rgba(148, 163, 184, 0.08);
        backdrop-filter: blur(12px);
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: var(--slate-400);
        border-radius: 12px;
        padding: 0.65rem 1.25rem;
        font-weight: 600;
        transition: all 0.3s ease;
        position: relative;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: var(--slate-200);
        background: rgba(16, 185, 129, 0.08);
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--emerald-500), var(--emerald-700)) !important;
        color: white !important;
        box-shadow:
            0 4px 12px rgba(16, 185, 129, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.1) !important;
    }

    .stTabs [data-baseweb="tab-panel"] {
        background:
            linear-gradient(145deg,
                rgba(30, 41, 59, 0.5) 0%,
                rgba(15, 23, 42, 0.7) 100%);
        border-radius: 16px;
        padding: 2rem;
        margin-top: 1rem;
        border: 1px solid rgba(148, 163, 184, 0.08);
        backdrop-filter: blur(12px);
    }

    /* ===== INPUT FIELDS ===== */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div {
        background:
            linear-gradient(145deg,
                rgba(15, 23, 42, 0.9) 0%,
                rgba(30, 41, 59, 0.7) 100%) !important;
        border: 1px solid rgba(148, 163, 184, 0.15) !important;
        border-radius: 12px !important;
        color: var(--slate-200) !important;
        padding: 0.75rem 1rem !important;
        transition: all 0.3s ease !important;
        backdrop-filter: blur(8px) !important;
    }

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--emerald-500) !important;
        box-shadow:
            0 0 0 3px rgba(16, 185, 129, 0.15),
            0 0 20px rgba(16, 185, 129, 0.1) !important;
        outline: none !important;
    }

    .stTextInput > div > div > input::placeholder,
    .stTextArea > div > div > textarea::placeholder {
        color: var(--slate-500) !important;
    }

    /* Number input */
    .stNumberInput > div > div > input {
        background: rgba(15, 23, 42, 0.9) !important;
        border: 1px solid rgba(148, 163, 184, 0.15) !important;
        border-radius: 12px !important;
        color: var(--slate-200) !important;
    }

    /* ===== EXPANDER ===== */
    .streamlit-expanderHeader {
        background:
            linear-gradient(145deg,
                rgba(30, 41, 59, 0.6) 0%,
                rgba(15, 23, 42, 0.8) 100%) !important;
        border-radius: 12px !important;
        color: var(--slate-200) !important;
        padding: 1rem !important;
        border: 1px solid rgba(148, 163, 184, 0.08) !important;
        transition: all 0.3s ease !important;
    }

    .streamlit-expanderHeader:hover {
        border-color: rgba(16, 185, 129, 0.2) !important;
        background: rgba(30, 41, 59, 0.8) !important;
    }

    .streamlit-expanderContent {
        background: rgba(15, 23, 42, 0.7) !important;
        border: 1px solid rgba(148, 163, 184, 0.08) !important;
        border-top: none !important;
        border-radius: 0 0 12px 12px !important;
        backdrop-filter: blur(12px) !important;
    }

    /* ===== DIVIDER ===== */
    hr {
        border: none !important;
        height: 1px !important;
        background: linear-gradient(90deg,
            transparent,
            rgba(148, 163, 184, 0.2) 20%,
            rgba(16, 185, 129, 0.3) 50%,
            rgba(148, 163, 184, 0.2) 80%,
            transparent) !important;
        margin: 2.5rem 0 !important;
    }

    /* ===== SECTION HEADERS ===== */
    .section-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 2rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid rgba(148, 163, 184, 0.08);
    }

    .section-header h2 {
        margin: 0;
        font-size: 1.35rem;
        font-weight: 700;
        font-family: 'Space Grotesk', sans-serif;
        color: var(--slate-100);
        letter-spacing: -0.02em;
    }

    .section-header .icon {
        width: 48px;
        height: 48px;
        background: linear-gradient(135deg, var(--emerald-500), var(--emerald-700));
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.4rem;
        box-shadow:
            0 4px 16px rgba(16, 185, 129, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.1);
    }

    .section-header .badge {
        background: rgba(16, 185, 129, 0.15);
        color: var(--emerald-400);
        padding: 0.3rem 0.75rem;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-left: auto;
    }

    /* ===== VERIFICATION MODAL ===== */
    .verification-modal {
        background:
            linear-gradient(145deg,
                rgba(30, 41, 59, 0.7) 0%,
                rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 20px;
        padding: 2rem;
        margin: 1.5rem 0;
        backdrop-filter: blur(16px);
        box-shadow:
            0 8px 32px rgba(0, 0, 0, 0.4),
            0 0 40px rgba(16, 185, 129, 0.08);
    }

    .verification-modal .source-text {
        background:
            linear-gradient(135deg,
                rgba(2, 6, 23, 0.8) 0%,
                rgba(15, 23, 42, 0.9) 100%);
        border-left: 4px solid var(--gold-500);
        border-radius: 0 12px 12px 0;
        padding: 1.25rem;
        font-style: italic;
        color: var(--slate-300);
        margin: 1.25rem 0;
        box-shadow: inset 0 2px 20px rgba(0, 0, 0, 0.2);
    }

    .verification-modal .confidence-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.35rem 0.9rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .verification-modal .confidence-badge.high {
        background: rgba(16, 185, 129, 0.15);
        color: var(--emerald-400);
        border: 1px solid rgba(16, 185, 129, 0.3);
    }

    .verification-modal .confidence-badge.medium {
        background: rgba(245, 158, 11, 0.15);
        color: var(--gold-400);
        border: 1px solid rgba(245, 158, 11, 0.3);
    }

    .verification-modal .confidence-badge.low {
        background: rgba(239, 68, 68, 0.15);
        color: var(--danger);
        border: 1px solid rgba(239, 68, 68, 0.3);
    }

    /* ===== DOWNLOAD SECTION ===== */
    .download-section {
        background:
            linear-gradient(135deg,
                rgba(45, 39, 28, 0.4) 0%,
                rgba(15, 23, 42, 0.8) 50%,
                rgba(45, 39, 28, 0.3) 100%);
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-radius: 20px;
        padding: 2rem;
        text-align: center;
        margin-top: 2.5rem;
        position: relative;
        overflow: hidden;
        backdrop-filter: blur(16px);
    }

    .download-section::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle at center, rgba(245, 158, 11, 0.08) 0%, transparent 50%);
        animation: downloadGlow 4s ease-in-out infinite;
    }

    @keyframes downloadGlow {
        0%, 100% { transform: scale(1); opacity: 0.5; }
        50% { transform: scale(1.1); opacity: 1; }
    }

    .download-section h3 {
        color: var(--gold-400);
        margin-bottom: 1.25rem;
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        position: relative;
    }

    .download-section .file-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
        filter: drop-shadow(0 4px 12px rgba(245, 158, 11, 0.3));
    }

    /* ===== SCROLLBAR ===== */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }

    ::-webkit-scrollbar-track {
        background: rgba(15, 23, 42, 0.5);
        border-radius: 5px;
    }

    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, var(--slate-600), var(--slate-700));
        border-radius: 5px;
        border: 2px solid rgba(15, 23, 42, 0.5);
    }

    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, var(--slate-500), var(--slate-600));
    }

    /* ===== PROGRESS BAR ===== */
    .stProgress > div > div > div {
        background: linear-gradient(90deg,
            var(--emerald-500),
            var(--emerald-400),
            var(--gold-400),
            var(--gold-500)) !important;
        background-size: 200% 100%;
        animation: progressShine 2s linear infinite;
        border-radius: 8px !important;
    }

    @keyframes progressShine {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }

    .stProgress > div {
        background: rgba(15, 23, 42, 0.8) !important;
        border-radius: 8px !important;
    }

    /* ===== SELECTBOX ===== */
    [data-baseweb="select"] {
        background:
            linear-gradient(145deg,
                rgba(15, 23, 42, 0.9) 0%,
                rgba(30, 41, 59, 0.7) 100%) !important;
        border-radius: 12px !important;
    }

    [data-baseweb="popover"] {
        background: rgba(15, 23, 42, 0.95) !important;
        border: 1px solid rgba(148, 163, 184, 0.15) !important;
        border-radius: 12px !important;
        backdrop-filter: blur(20px) !important;
    }

    /* ===== FILE UPLOADER ===== */
    [data-testid="stFileUploader"] {
        background:
            linear-gradient(145deg,
                rgba(30, 41, 59, 0.5) 0%,
                rgba(15, 23, 42, 0.7) 100%);
        border: 2px dashed rgba(148, 163, 184, 0.2);
        border-radius: 16px;
        padding: 1.5rem;
        transition: all 0.3s ease;
    }

    [data-testid="stFileUploader"]:hover {
        border-color: rgba(16, 185, 129, 0.5);
        background: rgba(16, 185, 129, 0.05);
    }

    /* ===== METRICS ===== */
    [data-testid="stMetric"] {
        background:
            linear-gradient(145deg,
                rgba(30, 41, 59, 0.6) 0%,
                rgba(15, 23, 42, 0.8) 100%);
        border-radius: 16px;
        padding: 1.25rem;
        border: 1px solid rgba(148, 163, 184, 0.08);
        backdrop-filter: blur(12px);
        transition: all 0.3s ease;
    }

    [data-testid="stMetric"]:hover {
        border-color: rgba(16, 185, 129, 0.2);
        transform: translateY(-2px);
    }

    [data-testid="stMetricValue"] {
        color: var(--emerald-400) !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
    }

    [data-testid="stMetricLabel"] {
        color: var(--slate-400) !important;
        text-transform: uppercase !important;
        font-size: 0.75rem !important;
        letter-spacing: 0.08em !important;
    }

    /* ===== CAT LOGO ANIMATION ===== */
    @keyframes float {
        0%, 100% { transform: translateY(0px) rotate(0deg); }
        25% { transform: translateY(-8px) rotate(-2deg); }
        50% { transform: translateY(-12px) rotate(0deg); }
        75% { transform: translateY(-8px) rotate(2deg); }
    }

    .muezza-logo {
        animation: float 4s ease-in-out infinite;
        font-size: 3.5rem;
        display: inline-block;
        filter: drop-shadow(0 8px 16px rgba(16, 185, 129, 0.3));
    }

    /* ===== SUCCESS/ERROR ALERTS ===== */
    .stAlert {
        border-radius: 12px !important;
        backdrop-filter: blur(12px) !important;
    }

    .stSuccess {
        background: rgba(16, 185, 129, 0.1) !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
    }

    .stError {
        background: rgba(239, 68, 68, 0.1) !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
    }

    .stWarning {
        background: rgba(245, 158, 11, 0.1) !important;
        border: 1px solid rgba(245, 158, 11, 0.3) !important;
    }

    .stInfo {
        background: rgba(59, 130, 246, 0.1) !important;
        border: 1px solid rgba(59, 130, 246, 0.3) !important;
    }

    /* ===== TOOLTIP ===== */
    [data-baseweb="tooltip"] {
        background: rgba(2, 6, 23, 0.95) !important;
        border: 1px solid rgba(148, 163, 184, 0.15) !important;
        border-radius: 10px !important;
        backdrop-filter: blur(20px) !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4) !important;
    }

    /* ===== RADIO BUTTONS ===== */
    .stRadio > div {
        background:
            linear-gradient(145deg,
                rgba(30, 41, 59, 0.5) 0%,
                rgba(15, 23, 42, 0.7) 100%);
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid rgba(148, 163, 184, 0.08);
    }

    .stRadio label {
        color: var(--slate-300) !important;
        transition: color 0.2s ease;
    }

    .stRadio label:hover {
        color: var(--emerald-400) !important;
    }

    /* ===== CHECKBOX ===== */
    .stCheckbox {
        background:
            linear-gradient(145deg,
                rgba(30, 41, 59, 0.4) 0%,
                rgba(15, 23, 42, 0.6) 100%);
        border-radius: 10px;
        padding: 0.75rem;
        border: 1px solid rgba(148, 163, 184, 0.08);
        transition: all 0.2s ease;
    }

    .stCheckbox:hover {
        border-color: rgba(16, 185, 129, 0.2);
    }

    /* ===== DATAFRAME ===== */
    .stDataFrame {
        border-radius: 16px !important;
        overflow: hidden !important;
        border: 1px solid rgba(148, 163, 184, 0.08) !important;
    }

    .stDataFrame [data-testid="stDataFrameResizable"] {
        background: rgba(15, 23, 42, 0.9) !important;
    }

    /* ===== SPINNER ===== */
    .stSpinner > div {
        border-color: var(--emerald-500) transparent transparent transparent !important;
    }

    /* ===== JSON VIEWER ===== */
    .stJson {
        background: rgba(2, 6, 23, 0.9) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(148, 163, 184, 0.1) !important;
    }

    /* ===== MULTISELECT ===== */
    .stMultiSelect [data-baseweb="tag"] {
        background: linear-gradient(135deg, var(--emerald-600), var(--emerald-700)) !important;
        border-radius: 8px !important;
    }

    /* ===== SLIDER ===== */
    .stSlider > div > div > div {
        background: var(--emerald-500) !important;
    }

    .stSlider [data-baseweb="slider"] [data-testid="stThumbValue"] {
        background: linear-gradient(135deg, var(--emerald-500), var(--emerald-700)) !important;
        border-radius: 8px !important;
    }

    /* ===== FLOATING PARTICLES (subtle) ===== */
    .stApp::after {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-image:
            radial-gradient(circle at 20% 80%, rgba(16, 185, 129, 0.03) 0%, transparent 20%),
            radial-gradient(circle at 80% 20%, rgba(245, 158, 11, 0.02) 0%, transparent 20%),
            radial-gradient(circle at 40% 40%, rgba(139, 92, 246, 0.02) 0%, transparent 15%);
        pointer-events: none;
        z-index: 0;
        animation: floatingParticles 30s ease-in-out infinite;
    }

    @keyframes floatingParticles {
        0%, 100% { opacity: 0.5; }
        50% { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================
def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        "slr_state": None,
        "orchestrator": None,
        "is_running": False,
        "progress": 0,
        "progress_message": "",
        "processing_log": [],
        "prisma_stats": PRISMAStats(),
        "agent_status": {
            "search": AgentStatus.PENDING,
            "screening": AgentStatus.PENDING,
            "acquisition": AgentStatus.PENDING,
            "quality": AgentStatus.PENDING,
        },
        "quality_distribution": {"HIGH": 0, "MODERATE": 0, "LOW": 0, "CRITICAL": 0},
        "results_df": None,
        "narrative_generator": None,
        "generated_narratives": None,
        "narrative_generating": False,
        "report_orchestrator": None,
        "full_report_chapters": None,
        "report_generating": False,
        "citation_stitcher": None,
        "continuity_report": None,
        "bibliography_loaded": False,
        "forensic_audit_result": None,
        "researcher_name": "Peneliti",
        "institution": "",
        "generated_bibliography": [],
        "verification_modal_open": False,
        "selected_paper_for_verification": None,
    }

    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

init_session_state()


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================
def check_configuration() -> Dict[str, bool]:
    """Check if required API keys are configured."""
    # Check if scholarly is available for Google Scholar
    try:
        from scholarly import scholarly
        scholarly_available = True
    except ImportError:
        scholarly_available = False

    return {
        "anthropic": bool(settings.anthropic_api_key),
        "scopus": bool(settings.scopus_api_key),
        "semantic_scholar": bool(settings.semantic_scholar_api_key),
        "core": bool(getattr(settings, 'core_api_key', None)),
        "unpaywall": bool(settings.unpaywall_email),
        "doaj": True,  # DOAJ is always available (free public API)
        "google_scholar": scholarly_available,  # Available if scholarly installed
        # New expanded waterfall sources
        "openalex": True,  # OpenAlex is always available (free, no API key required)
        "crossref": True,  # Crossref is always available (free public API)
        "pubmed": True,  # PubMed is always available (free, API key optional)
        "pubmed_enhanced": bool(getattr(settings, 'ncbi_api_key', None)),  # Enhanced rate limits with key
    }


def add_log_entry(message: str, agent: str = "Muezza", log_type: str = "info"):
    """Add entry to processing log."""
    timestamp = datetime.now().strftime('%H:%M:%S')
    entry = {
        "timestamp": timestamp,
        "agent": agent,
        "message": message,
        "type": log_type
    }
    st.session_state.processing_log.append(entry)


def render_api_status_indicator(name: str, is_configured: bool):
    """Render a single API status indicator."""
    status_class = "online" if is_configured else "offline"
    status_text = "Connected" if is_configured else "Not Configured"

    st.markdown(f"""
    <div class="api-status">
        <span class="dot {status_class}"></span>
        <span class="name">{name}</span>
        <span style="margin-left: auto; font-size: 0.75rem; color: var(--slate-500);">{status_text}</span>
    </div>
    """, unsafe_allow_html=True)


def render_agent_card(icon: str, name: str, description: str, status: AgentStatus):
    """Render an agent status card."""
    status_class = status.value.lower()
    status_text = {
        AgentStatus.PENDING: "Waiting...",
        AgentStatus.ACTIVE: "Running",
        AgentStatus.COMPLETED: "Completed",
        AgentStatus.ERROR: "Error"
    }
    status_icon = {
        AgentStatus.PENDING: "⏳",
        AgentStatus.ACTIVE: "🔄",
        AgentStatus.COMPLETED: "✅",
        AgentStatus.ERROR: "❌"
    }

    st.markdown(f"""
    <div class="agent-card {status_class}">
        <div class="agent-icon">{icon}</div>
        <p class="agent-name">{name}</p>
        <p class="agent-status {status_class}">{status_icon[status]} {status_text[status]}</p>
        <p style="font-size: 0.75rem; color: var(--slate-500); margin-top: 0.5rem;">{description}</p>
    </div>
    """, unsafe_allow_html=True)


def render_metric_card(value: int, label: str, icon: str):
    """Render a PRISMA metric card."""
    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">{icon}</div>
        <div class="number">{value}</div>
        <div class="label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def render_terminal_log():
    """Render the terminal-style processing log."""
    st.markdown('<div class="terminal-log">', unsafe_allow_html=True)

    if not st.session_state.processing_log:
        st.markdown("""
        <div class="log-entry">
            <span class="timestamp">[--:--:--]</span>
            <span class="agent-name">Muezza</span>
            <span style="color: var(--slate-400);"> is ready and waiting for your command...</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        for entry in st.session_state.processing_log[-15:]:
            type_class = entry.get("type", "info")
            st.markdown(f"""
            <div class="log-entry">
                <span class="timestamp">[{entry['timestamp']}]</span>
                <span class="agent-name">{entry['agent']}</span>
                <span class="{type_class}"> {entry['message']}</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def render_prisma_sankey(stats: PRISMAStats):
    """Render PRISMA 2020 Sankey diagram with premium styling."""

    fig = go.Figure(data=[go.Sankey(
        arrangement='snap',
        node=dict(
            pad=20,
            thickness=25,
            line=dict(color="rgba(16, 185, 129, 0.5)", width=1),
            label=[
                f"Identified<br>n={stats.identified}",
                f"After Dedup<br>n={stats.identified - stats.duplicates_removed}",
                f"Screened<br>n={stats.screened}",
                f"Sought<br>n={stats.sought_retrieval}",
                f"Assessed<br>n={stats.assessed_eligibility}",
                f"Included<br>n={stats.included_synthesis}",
                f"Duplicates<br>n={stats.duplicates_removed}",
                f"Excluded<br>n={stats.excluded_screening}",
                f"Not Retrieved<br>n={stats.not_retrieved}",
                f"Excluded<br>n={stats.excluded_eligibility}"
            ],
            color=[
                "#10b981",  # Identified - emerald
                "#34d399",  # After Dedup
                "#6ee7b7",  # Screened
                "#fbbf24",  # Sought - gold
                "#f59e0b",  # Assessed
                "#10b981",  # Included - emerald
                "#64748b",  # Duplicates - slate
                "#ef4444",  # Excluded screening - red
                "#94a3b8",  # Not retrieved
                "#dc2626"   # Excluded eligibility
            ],
            customdata=[
                "Papers identified from databases",
                "After duplicate removal",
                "Screened by title/abstract",
                "Full-text retrieval attempted",
                "Assessed for eligibility",
                "Included in synthesis",
                "Duplicate records removed",
                "Excluded at screening",
                "Could not retrieve full-text",
                "Excluded after assessment"
            ],
            hovertemplate='%{label}<br>%{customdata}<extra></extra>'
        ),
        link=dict(
            source=[0, 1, 2, 2, 3, 3, 4, 4],
            target=[1, 2, 3, 7, 4, 8, 5, 9],
            value=[
                max(1, stats.identified - stats.duplicates_removed),
                max(1, stats.screened),
                max(1, stats.sought_retrieval),
                max(1, stats.excluded_screening),
                max(1, stats.assessed_eligibility),
                max(1, stats.not_retrieved),
                max(1, stats.included_synthesis),
                max(1, stats.excluded_eligibility)
            ],
            color=[
                "rgba(16, 185, 129, 0.3)",
                "rgba(52, 211, 153, 0.3)",
                "rgba(110, 231, 183, 0.3)",
                "rgba(239, 68, 68, 0.2)",
                "rgba(251, 191, 36, 0.3)",
                "rgba(148, 163, 184, 0.2)",
                "rgba(16, 185, 129, 0.4)",
                "rgba(220, 38, 38, 0.2)"
            ]
        )
    )])

    fig.update_layout(
        title=dict(
            text="PRISMA 2020 Flow Diagram",
            font=dict(color="#e2e8f0", size=16),
            x=0.5
        ),
        font=dict(color="#94a3b8", size=11),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=450,
        margin=dict(l=20, r=20, t=50, b=20)
    )

    return fig


def render_quality_chart(distribution: Dict[str, int]):
    """Render quality distribution chart."""
    colors = {
        "HIGH": "#10b981",
        "MODERATE": "#fbbf24",
        "LOW": "#f97316",
        "CRITICAL": "#ef4444"
    }

    fig = go.Figure(data=[
        go.Bar(
            x=list(distribution.keys()),
            y=list(distribution.values()),
            marker_color=[colors.get(k, "#64748b") for k in distribution.keys()],
            text=list(distribution.values()),
            textposition='auto',
            textfont=dict(color='white', size=14, family='Arial Black'),
            hovertemplate='<b>%{x}</b><br>Papers: %{y}<extra></extra>'
        )
    ])

    fig.update_layout(
        title=dict(
            text="Quality Assessment Distribution",
            font=dict(color="#e2e8f0", size=14),
            x=0.5
        ),
        xaxis=dict(
            title="Quality Category",
            color="#94a3b8",
            gridcolor="rgba(100, 116, 139, 0.2)"
        ),
        yaxis=dict(
            title="Number of Papers",
            color="#94a3b8",
            gridcolor="rgba(100, 116, 139, 0.2)"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=300,
        margin=dict(l=20, r=20, t=50, b=20),
        bargap=0.3
    )

    return fig


def progress_callback(phase: str, percent: int, message: str):
    """Callback for progress updates from the orchestrator."""
    st.session_state.progress = percent
    st.session_state.progress_message = message

    # Determine agent name for log
    agent_names = {
        "search": "Search Strategist",
        "screening": "Screening Specialist",
        "acquisition": "Waterfall Retrieval",
        "quality": "Quality Evaluator"
    }

    agent_name = agent_names.get(phase, "Muezza")

    # Update agent status
    if percent >= 0:
        if phase == "search":
            st.session_state.agent_status["search"] = AgentStatus.ACTIVE if percent < 25 else AgentStatus.COMPLETED
        elif phase == "screening":
            st.session_state.agent_status["screening"] = AgentStatus.ACTIVE if percent < 50 else AgentStatus.COMPLETED
        elif phase == "acquisition":
            st.session_state.agent_status["acquisition"] = AgentStatus.ACTIVE if percent < 75 else AgentStatus.COMPLETED
        elif phase == "quality":
            st.session_state.agent_status["quality"] = AgentStatus.ACTIVE if percent < 100 else AgentStatus.COMPLETED
    else:
        st.session_state.agent_status[phase] = AgentStatus.ERROR

    # Add to log
    add_log_entry(message, agent_name, "action")


async def run_slr_pipeline(
    research_question: str,
    inclusion_criteria: List[str],
    exclusion_criteria: List[str],
    date_range: tuple
):
    """Run the SLR pipeline asynchronously."""
    orchestrator = SLROrchestrator(progress_callback=progress_callback)

    st.session_state.orchestrator = orchestrator
    st.session_state.is_running = True

    add_log_entry("Starting systematic literature review pipeline...", "Muezza", "action")

    try:
        final_state = await orchestrator.run(
            research_question=research_question,
            inclusion_criteria=inclusion_criteria,
            exclusion_criteria=exclusion_criteria,
            date_range=date_range
        )

        st.session_state.slr_state = final_state

        if final_state:
            stats = final_state.get("prisma_stats", {})
            st.session_state.prisma_stats = PRISMAStats(
                identified=stats.get("identified", 0),
                duplicates_removed=stats.get("duplicates_removed", 0),
                screened=stats.get("screened", 0),
                excluded_screening=stats.get("excluded_screening", 0),
                sought_retrieval=stats.get("sought_retrieval", 0),
                not_retrieved=stats.get("not_retrieved", 0),
                assessed_eligibility=stats.get("assessed_eligibility", 0),
                excluded_eligibility=stats.get("excluded_eligibility", 0),
                included_synthesis=stats.get("included_synthesis", 0),
            )

            synthesis_papers = final_state.get("synthesis_ready", [])
            sensitivity_papers = final_state.get("sensitivity_analysis", [])
            excluded_papers = final_state.get("excluded_quality", [])

            st.session_state.quality_distribution = {
                "HIGH": sum(1 for p in synthesis_papers if p.get("quality_category") == "HIGH"),
                "MODERATE": sum(1 for p in synthesis_papers if p.get("quality_category") == "MODERATE"),
                "LOW": len(sensitivity_papers),
                "CRITICAL": len(excluded_papers),
            }

            all_assessed = final_state.get("assessed_papers", [])
            if all_assessed:
                st.session_state.results_df = pd.DataFrame([
                    {
                        "Title": p.get("title", "")[:80] + "..." if len(p.get("title", "")) > 80 else p.get("title", ""),
                        "Source": p.get("full_text_source", "N/A"),
                        "Method": p.get("retrieval_method", "N/A"),
                        "Quality": p.get("quality_score", 0),
                        "Category": p.get("quality_category", "N/A"),
                        "DOI": p.get("doi", ""),
                    }
                    for p in all_assessed
                ])

        add_log_entry("Pipeline completed successfully!", "Muezza", "success")

    except Exception as e:
        add_log_entry(f"Pipeline failed: {str(e)}", "Muezza", "error")
    finally:
        st.session_state.is_running = False


# ============================================================================
# MAIN APPLICATION
# ============================================================================
def main():
    """Main application entry point."""

    # ========== HEADER ==========
    st.markdown(f"""
    <div class="main-header">
        <div style="display: flex; align-items: center; gap: 1rem;">
            <span class="muezza-logo">🐱</span>
            <div>
                <h1>{APP_INFO['name']} <span class="version-badge">v{APP_INFO['version']}</span></h1>
                <p class="tagline">{APP_INFO['tagline']} — {APP_INFO['description']}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ========== SIDEBAR ==========
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem 0; border-bottom: 1px solid var(--slate-700); margin-bottom: 1rem;">
            <span style="font-size: 2.5rem;">🐱</span>
            <h2 style="margin: 0.5rem 0 0 0; color: var(--emerald-400);">{APP_INFO['name']}</h2>
            <p style="font-size: 0.8rem; color: var(--slate-400); margin: 0;">Command Center</p>
            <p style="font-size: 0.65rem; color: var(--gold-400); margin: 0.25rem 0 0 0;">v{APP_INFO['version']}</p>
        </div>
        """, unsafe_allow_html=True)

        # API Status Section
        st.markdown("### 🔌 API Status")
        config = check_configuration()

        # Primary Sources
        st.caption("Primary Sources")
        render_api_status_indicator("Scopus", config["scopus"])
        render_api_status_indicator("Semantic Scholar", config["semantic_scholar"])
        render_api_status_indicator("Claude AI", config["anthropic"])

        # Expanded Waterfall Sources
        st.caption("Waterfall Sources")
        render_api_status_indicator("Unpaywall", config["unpaywall"])
        render_api_status_indicator("OpenAlex", config["openalex"])
        render_api_status_indicator("Crossref", config["crossref"])
        render_api_status_indicator("PubMed/PMC", config["pubmed"])
        render_api_status_indicator("DOAJ", config["doaj"])
        render_api_status_indicator("CORE", config.get("core", False))
        render_api_status_indicator("Google Scholar", config["google_scholar"])

        # Cache Status
        try:
            from api.search_cache import get_search_cache
            cache = get_search_cache()
            cache_stats = cache.get_stats()
            with st.expander("🚀 Cache Status", expanded=False):
                st.markdown(f"""
                <div style="font-size: 0.8rem; color: var(--slate-300);">
                    <p>📊 Hit Rate: <strong style="color: var(--emerald-400);">{cache_stats['hit_rate']}</strong></p>
                    <p>💾 Entries: {cache_stats['entries']}/{cache_stats['max_entries']}</p>
                    <p>✅ Hits: {cache_stats['hits']} | ❌ Misses: {cache_stats['misses']}</p>
                </div>
                """, unsafe_allow_html=True)
        except:
            pass

        st.markdown("---")

        # Research Question
        st.markdown("### 🎯 Research Question")
        research_question = st.text_area(
            "Define your research question",
            placeholder="e.g., What is the effectiveness of machine learning in medical diagnosis?",
            height=100,
            label_visibility="collapsed"
        )

        st.markdown("---")

        # Inclusion Criteria
        st.markdown("### ✅ Inclusion Criteria")
        inclusion_text = st.text_area(
            "One criterion per line",
            placeholder="Published 2019-2024\nEnglish language\nPeer-reviewed journals\nEmpirical studies",
            height=100,
            label_visibility="collapsed"
        )

        # Exclusion Criteria
        st.markdown("### ❌ Exclusion Criteria")
        exclusion_text = st.text_area(
            "One criterion per line",
            placeholder="Conference abstracts only\nCase reports\nOpinion pieces\nNon-English",
            height=100,
            label_visibility="collapsed"
        )

        st.markdown("---")

        # Date Range
        st.markdown("### 📅 Publication Period")
        date_cols = st.columns(2)
        with date_cols[0]:
            start_year = st.number_input("From", min_value=1990, max_value=2026, value=2019)
        with date_cols[1]:
            end_year = st.number_input("To", min_value=1990, max_value=2026, value=2024)

        st.markdown("---")

        # Action Buttons
        col1, col2 = st.columns(2)
        with col1:
            run_button = st.button(
                "🚀 Start",
                type="primary",
                width="stretch",
                disabled=st.session_state.is_running
            )
        with col2:
            reset_button = st.button(
                "🔄 Reset",
                width="stretch"
            )

        if reset_button:
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            init_session_state()
            st.rerun()

    # ========== MAIN CONTENT ==========

    # Agent Status Cards Row
    st.markdown("""
    <div class="section-header">
        <div class="icon">🤖</div>
        <h2>Agent Status Monitor</h2>
    </div>
    """, unsafe_allow_html=True)

    agent_cols = st.columns(4)

    agents_config = [
        ("🔍", "Search Strategist", "Boolean query & database search", "search"),
        ("🔬", "Screening Specialist", "Title/Abstract AI screening", "screening"),
        ("📥", "Waterfall Retrieval", "Multi-source full-text fetch", "acquisition"),
        ("⚖️", "Quality Evaluator", "JBI critical appraisal", "quality"),
    ]

    for col, (icon, name, desc, key) in zip(agent_cols, agents_config):
        with col:
            render_agent_card(icon, name, desc, st.session_state.agent_status[key])

    st.markdown("---")

    # Two Column Layout: PRISMA + Log
    main_col1, main_col2 = st.columns([2, 1])

    with main_col1:
        st.markdown("""
        <div class="section-header">
            <div class="icon">📊</div>
            <h2>PRISMA 2020 Flow</h2>
        </div>
        """, unsafe_allow_html=True)

        # PRISMA Metrics Row
        metric_cols = st.columns(5)
        stats = st.session_state.prisma_stats
        metrics_config = [
            (stats.identified, "Identified", "🔵"),
            (stats.screened, "Screened", "🟢"),
            (stats.sought_retrieval, "Retrieved", "🟡"),
            (stats.assessed_eligibility, "Assessed", "🟠"),
            (stats.included_synthesis, "Included", "✅"),
        ]

        for col, (value, label, icon) in zip(metric_cols, metrics_config):
            with col:
                render_metric_card(value, label, icon)

        st.markdown("<br>", unsafe_allow_html=True)

        # Sankey Diagram
        st.plotly_chart(
            render_prisma_sankey(stats),
            width="stretch",
            config={'displayModeBar': False}
        )

    with main_col2:
        st.markdown("""
        <div class="section-header">
            <div class="icon">📋</div>
            <h2>Processing Log</h2>
        </div>
        """, unsafe_allow_html=True)

        render_terminal_log()

        # Quality Distribution (if data available)
        if sum(st.session_state.quality_distribution.values()) > 0:
            st.markdown("<br>", unsafe_allow_html=True)
            st.plotly_chart(
                render_quality_chart(st.session_state.quality_distribution),
                width="stretch",
                config={'displayModeBar': False}
            )

    # Run Pipeline
    if run_button and research_question:
        inclusion_criteria = [c.strip() for c in inclusion_text.split('\n') if c.strip()]
        exclusion_criteria = [c.strip() for c in exclusion_text.split('\n') if c.strip()]

        add_log_entry(f"Research question received: {research_question[:50]}...", "Muezza", "info")

        progress_bar = st.progress(0)
        status_text = st.empty()

        with st.spinner("Muezza is working on your systematic review..."):
            asyncio.run(run_slr_pipeline(
                research_question=research_question,
                inclusion_criteria=inclusion_criteria,
                exclusion_criteria=exclusion_criteria,
                date_range=(start_year, end_year)
            ))

        st.success("🎉 Systematic review completed!")
        st.balloons()
        st.rerun()

    # ========== FORENSIC AUDIT TABLE ==========
    if st.session_state.results_df is not None and not st.session_state.results_df.empty:
        st.markdown("---")
        st.markdown("""
        <div class="section-header">
            <div class="icon">🔬</div>
            <h2>Forensic Audit Results</h2>
        </div>
        """, unsafe_allow_html=True)

        # Create styled dataframe
        df = st.session_state.results_df.copy()

        # Add verification button column indicator
        df['Verify'] = '🔍 Verify'

        # Display table
        st.dataframe(
            df,
            width="stretch",
            height=400,
            column_config={
                "Title": st.column_config.TextColumn("Paper Title", width="large"),
                "Source": st.column_config.TextColumn("Source", width="small"),
                "Method": st.column_config.TextColumn("Retrieval", width="small"),
                "Quality": st.column_config.ProgressColumn("Quality Score", min_value=0, max_value=100),
                "Category": st.column_config.TextColumn("Category", width="small"),
                "DOI": st.column_config.TextColumn("DOI", width="medium"),
                "Verify": st.column_config.TextColumn("Action", width="small"),
            }
        )

        # Verification Modal
        st.markdown("### 🔍 Citation Verification")

        verify_cols = st.columns([3, 1])
        with verify_cols[0]:
            selected_doi = st.selectbox(
                "Select paper to verify",
                options=df['DOI'].tolist(),
                format_func=lambda x: f"{x}" if x else "No DOI available"
            )

        with verify_cols[1]:
            verify_btn = st.button("🔬 Verify Citation", type="primary", width="stretch")

        if verify_btn and selected_doi:
            paper_row = df[df['DOI'] == selected_doi].iloc[0]

            st.markdown(f"""
            <div class="verification-modal">
                <h4 style="color: var(--emerald-400); margin-bottom: 1rem;">📄 Verification Report</h4>
                <p><strong>Title:</strong> {paper_row['Title']}</p>
                <p><strong>DOI:</strong> <a href="https://doi.org/{selected_doi}" target="_blank" style="color: var(--gold-400);">{selected_doi}</a></p>
                <p><strong>Source:</strong> {paper_row['Source']} | <strong>Method:</strong> {paper_row['Method']}</p>

                <div class="source-text">
                    <p style="font-size: 0.9rem; color: var(--slate-400); margin-bottom: 0.5rem;">📝 Extracted Abstract/Key Passage:</p>
                    "This study investigates the application of [methodology] in [domain].
                    Our findings suggest that [key finding] with statistical significance (p < 0.05).
                    The implications for [field] are discussed..."
                </div>

                <div style="display: flex; gap: 1rem; margin-top: 1rem;">
                    <span class="confidence-badge high">✅ Verified Source</span>
                    <span class="confidence-badge medium">Quality: {paper_row['Quality']}%</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Export Options
        st.markdown("---")
        export_cols = st.columns(4)

        with export_cols[0]:
            csv_data = st.session_state.results_df.to_csv(index=False)
            st.download_button(
                label="📄 Export CSV",
                data=csv_data,
                file_name="muezza_audit_results.csv",
                mime="text/csv",
                width="stretch"
            )

        with export_cols[1]:
            json_data = st.session_state.results_df.to_json(orient="records", indent=2)
            st.download_button(
                label="📋 Export JSON",
                data=json_data,
                file_name="muezza_audit_results.json",
                mime="application/json",
                width="stretch"
            )

        with export_cols[2]:
            st.button("📊 Export PRISMA", width="stretch")

        with export_cols[3]:
            st.button("📧 Share Report", width="stretch", disabled=True)

    # ========== BIBLIOMETRIC ANALYSIS ==========
    if st.session_state.slr_state and st.session_state.slr_state.get("synthesis_ready"):
        st.markdown("---")
        st.markdown("""
        <div class="section-header">
            <div class="icon">📊</div>
            <h2>Bibliometric Analysis</h2>
        </div>
        """, unsafe_allow_html=True)

        # Get papers for analysis
        papers_for_analysis = st.session_state.slr_state.get("synthesis_ready", [])

        if papers_for_analysis:
            from agents.bibliometric_agent import (
                BibliometricAgent,
                create_publication_trend_chart,
                create_journal_distribution_chart,
                create_citation_distribution_chart,
                create_author_chart,
                create_keyword_chart,
            )

            # Perform analysis
            biblio_agent = BibliometricAgent(papers_for_analysis)
            stats = biblio_agent.analyze()

            # Summary Metrics Row
            metric_cols = st.columns(6)
            with metric_cols[0]:
                st.metric("Total Papers", stats.total_papers)
            with metric_cols[1]:
                st.metric("Total Citations", f"{stats.total_citations:,}")
            with metric_cols[2]:
                st.metric("Avg Citations", f"{stats.avg_citations:.1f}")
            with metric_cols[3]:
                st.metric("H-Index", stats.h_index)
            with metric_cols[4]:
                st.metric("Max Citations", stats.max_citations)
            with metric_cols[5]:
                st.metric("With Citations", f"{stats.papers_with_citations}")

            st.markdown("---")

            # Charts Row 1: Publication Trends & Citation Distribution
            chart_cols1 = st.columns(2)

            with chart_cols1[0]:
                if stats.publication_years:
                    trend_fig = create_publication_trend_chart(stats.publication_years)
                    if trend_fig:
                        st.plotly_chart(trend_fig, width="stretch")
                else:
                    st.info("No publication year data available")

            with chart_cols1[1]:
                if stats.citation_distribution:
                    cite_fig = create_citation_distribution_chart(stats.citation_distribution)
                    if cite_fig:
                        st.plotly_chart(cite_fig, width="stretch")
                else:
                    st.info("No citation data available")

            # Charts Row 2: Journal Distribution & Top Authors
            chart_cols2 = st.columns(2)

            with chart_cols2[0]:
                if stats.top_journals:
                    journal_fig = create_journal_distribution_chart(stats.top_journals)
                    if journal_fig:
                        st.plotly_chart(journal_fig, width="stretch")
                else:
                    st.info("No journal data available")

            with chart_cols2[1]:
                if stats.top_authors:
                    author_fig = create_author_chart(stats.top_authors)
                    if author_fig:
                        st.plotly_chart(author_fig, width="stretch")
                else:
                    st.info("No author data available")

            # Charts Row 3: Keywords
            if stats.top_keywords:
                st.markdown("#### Top Keywords")
                keyword_fig = create_keyword_chart(stats.top_keywords)
                if keyword_fig:
                    st.plotly_chart(keyword_fig, width="stretch")

            # Top Cited Papers Table
            if stats.top_cited_papers:
                st.markdown("#### Top Cited Papers")
                top_cited_data = []
                for i, paper in enumerate(stats.top_cited_papers[:10], 1):
                    authors = paper.get('authors', [])
                    if isinstance(authors, list):
                        author_str = ', '.join(authors[:3])
                        if len(authors) > 3:
                            author_str += ' et al.'
                    else:
                        author_str = str(authors)

                    top_cited_data.append({
                        'Rank': i,
                        'Title': paper.get('title', '')[:80] + ('...' if len(paper.get('title', '')) > 80 else ''),
                        'Authors': author_str,
                        'Year': paper.get('year', ''),
                        'Citations': paper.get('citations', 0)
                    })

                import pandas as pd
                top_cited_df = pd.DataFrame(top_cited_data)
                st.dataframe(
                    top_cited_df,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Rank": st.column_config.NumberColumn("Rank", width="small"),
                        "Title": st.column_config.TextColumn("Paper Title", width="large"),
                        "Authors": st.column_config.TextColumn("Authors", width="medium"),
                        "Year": st.column_config.TextColumn("Year", width="small"),
                        "Citations": st.column_config.NumberColumn("Citations", width="small"),
                    }
                )
        else:
            st.info("Run SLR analysis first to see bibliometric data.")

    # ========== CITATION NETWORK EXPLORER ==========
    if st.session_state.slr_state and st.session_state.slr_state.get("synthesis_ready"):
        st.markdown("---")
        st.markdown("""
        <div class="section-header">
            <div class="icon">🕸️</div>
            <h2>Citation Network Explorer</h2>
        </div>
        """, unsafe_allow_html=True)

        papers_for_network = st.session_state.slr_state.get("synthesis_ready", [])

        if papers_for_network:
            try:
                from agents.citation_network_agent import CitationNetworkAgent, NETWORKX_AVAILABLE
                from agents.citation_context_analyzer import CitationContextAnalyzer

                if not NETWORKX_AVAILABLE:
                    st.warning("NetworkX library not installed. Run: pip install networkx")
                else:
                    # Network Analysis Controls
                    net_cols = st.columns([1, 1, 2])
                    with net_cols[0]:
                        max_depth = st.slider("Network Depth", 1, 3, 1, help="How many citation layers to explore")
                    with net_cols[1]:
                        max_papers = st.slider("Max Papers", 20, 100, 50, help="Maximum papers in network")

                    if st.button("Build Citation Network", type="secondary"):
                        with st.spinner("Building citation network..."):
                            agent = CitationNetworkAgent(
                                s2_api_key=settings.semantic_scholar_api_key,
                                max_depth=max_depth,
                                max_papers=max_papers
                            )

                            network = agent.build_network(papers_for_network)

                            if network and network.nodes:
                                # Store in session state
                                st.session_state.citation_network = network.to_dict()

                                # Display metrics
                                metric_cols = st.columns(4)
                                with metric_cols[0]:
                                    st.metric("Papers in Network", len(network.nodes))
                                with metric_cols[1]:
                                    st.metric("Citation Links", len(network.edges))
                                with metric_cols[2]:
                                    st.metric("Research Clusters", len(network.clusters))
                                with metric_cols[3]:
                                    seed_count = sum(1 for n in network.nodes if n.is_seed)
                                    st.metric("Seed Papers", seed_count)

                                st.markdown("---")

                                # Network Visualization
                                st.markdown("#### Network Visualization")
                                try:
                                    plotly_data = network.to_plotly_data()
                                    if plotly_data.get('node_x'):
                                        import plotly.graph_objects as go

                                        # Create edge trace
                                        edge_trace = go.Scatter(
                                            x=plotly_data['edge_x'],
                                            y=plotly_data['edge_y'],
                                            mode='lines',
                                            line=dict(width=0.5, color='#888'),
                                            hoverinfo='none'
                                        )

                                        # Create node trace
                                        node_trace = go.Scatter(
                                            x=plotly_data['node_x'],
                                            y=plotly_data['node_y'],
                                            mode='markers+text',
                                            hovertext=plotly_data['node_text'],
                                            hoverinfo='text',
                                            marker=dict(
                                                size=plotly_data['node_size'],
                                                color=plotly_data['node_color'],
                                                colorscale='Viridis',
                                                line_width=2
                                            )
                                        )

                                        fig = go.Figure(
                                            data=[edge_trace, node_trace],
                                            layout=go.Layout(
                                                title='Citation Network Graph',
                                                titlefont_size=16,
                                                showlegend=False,
                                                hovermode='closest',
                                                margin=dict(b=20, l=5, r=5, t=40),
                                                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                                height=500
                                            )
                                        )
                                        st.plotly_chart(fig, use_container_width=True)
                                except Exception as e:
                                    st.warning(f"Could not render network visualization: {e}")

                                # Key Papers Table
                                st.markdown("#### Key Papers by Centrality")
                                key_papers = agent.get_key_papers(10)
                                if key_papers:
                                    key_data = []
                                    for i, paper in enumerate(key_papers, 1):
                                        key_data.append({
                                            'Rank': i,
                                            'Title': paper.title[:60] + ('...' if len(paper.title) > 60 else ''),
                                            'Year': paper.year,
                                            'Citations': paper.citations,
                                            'Centrality': f"{paper.centrality_score:.4f}",
                                            'Cluster': paper.cluster_id
                                        })
                                    st.dataframe(pd.DataFrame(key_data), hide_index=True)

                                # Cluster Summary
                                st.markdown("#### Research Clusters")
                                cluster_summary = agent.get_cluster_summary()
                                if cluster_summary:
                                    cluster_cols = st.columns(min(len(cluster_summary), 4))
                                    for i, (cluster_id, summary) in enumerate(cluster_summary.items()):
                                        with cluster_cols[i % len(cluster_cols)]:
                                            st.markdown(f"**Cluster {cluster_id}**")
                                            st.caption(f"{summary['paper_count']} papers")
                                            st.caption(f"Years: {summary['year_range'][0]}-{summary['year_range'][1]}")
                                            if summary['top_papers']:
                                                st.caption(f"Top: {summary['top_papers'][0][1][:30]}...")

                                st.success("Citation network built successfully!")
                            else:
                                st.warning("Could not build network - no related papers found")

                    # Display existing network if available
                    if hasattr(st.session_state, 'citation_network') and st.session_state.citation_network:
                        st.info(f"Network cached: {st.session_state.citation_network.get('node_count', 0)} papers, {st.session_state.citation_network.get('edge_count', 0)} links")

            except ImportError as e:
                st.warning(f"Citation network features require additional libraries: {e}")
            except Exception as e:
                st.error(f"Error loading citation network: {e}")
        else:
            st.info("Run SLR analysis first to build citation network.")

    # ========== DRAFTING PREVIEW ==========
    st.markdown("---")
    st.markdown("""
    <div class="section-header">
        <div class="icon">📝</div>
        <h2>Research Report Drafting</h2>
    </div>
    """, unsafe_allow_html=True)

    # Author Information
    author_cols = st.columns([2, 2, 1])

    with author_cols[0]:
        researcher_name = st.text_input(
            "👤 Researcher Name",
            value=st.session_state.researcher_name,
            placeholder="Dr. Ahmad Researcher"
        )
        if researcher_name:
            st.session_state.researcher_name = researcher_name

    with author_cols[1]:
        institution = st.text_input(
            "🏛️ Institution",
            value=st.session_state.institution,
            placeholder="Universitas Indonesia"
        )
        if institution:
            st.session_state.institution = institution

    with author_cols[2]:
        use_ai = st.checkbox("🤖 Use Claude AI", value=True)

    # Generate Report Button
    if st.session_state.slr_state:
        generate_btn = st.button(
            "✨ Generate Full Report",
            type="primary",
            width="stretch",
            disabled=st.session_state.report_generating
        )

        if generate_btn:
            st.session_state.report_generating = True

            with st.spinner("Muezza is crafting your research report..."):
                try:
                    add_log_entry("Starting report generation...", "Muezza", "action")

                    # Prepare data
                    scopus_metadata = {
                        "total_results": st.session_state.prisma_stats.identified,
                        "year_range": f"{start_year}-{end_year}",
                    }

                    extraction_table = st.session_state.slr_state.get("synthesis_ready", [])
                    if not extraction_table:
                        extraction_table = st.session_state.slr_state.get("assessed_papers", [])

                    prisma_stats = {
                        "identified": st.session_state.prisma_stats.identified,
                        "duplicates_removed": st.session_state.prisma_stats.duplicates_removed,
                        "screened": st.session_state.prisma_stats.screened,
                        "excluded_screening": st.session_state.prisma_stats.excluded_screening,
                        "sought_retrieval": st.session_state.prisma_stats.sought_retrieval,
                        "not_retrieved": st.session_state.prisma_stats.not_retrieved,
                        "assessed_eligibility": st.session_state.prisma_stats.assessed_eligibility,
                        "excluded_eligibility": st.session_state.prisma_stats.excluded_eligibility,
                        "included_synthesis": st.session_state.prisma_stats.included_synthesis,
                    }

                    papers = st.session_state.slr_state.get("synthesis_ready", [])

                    # Initialize orchestrator
                    api_key = settings.anthropic_api_key if use_ai else None
                    orchestrator = NarrativeOrchestrator(api_key=api_key)

                    # Generate all chapters
                    progress_bar = st.progress(0)

                    chapters = ["Bab 1", "Bab 2", "Bab 3", "Bab 4", "Bab 5"]
                    for i, chapter in enumerate(chapters):
                        add_log_entry(f"Generating {chapter}...", "Muezza", "action")
                        progress_bar.progress((i + 1) / len(chapters))

                        if chapter == "Bab 1":
                            orchestrator.generate_bab_1_pendahuluan(research_question, scopus_metadata)
                        elif chapter == "Bab 2":
                            orchestrator.generate_bab_2_tinjauan_pustaka(research_question, papers)
                        elif chapter == "Bab 3":
                            orchestrator.generate_bab_3_metodologi(prisma_stats)
                        elif chapter == "Bab 4":
                            orchestrator.generate_bab_4_hasil_pembahasan(research_question, extraction_table)
                        elif chapter == "Bab 5":
                            orchestrator.generate_bab_5_kesimpulan(research_question)

                    st.session_state.report_orchestrator = orchestrator
                    st.session_state.full_report_chapters = orchestrator.chapters

                    add_log_entry("Report generation completed!", "Muezza", "success")
                    st.success("✨ Research report generated successfully!")

                except Exception as e:
                    add_log_entry(f"Error: {str(e)}", "Muezza", "error")
                    st.error(f"Error generating report: {str(e)}")
                finally:
                    st.session_state.report_generating = False
                    st.rerun()

    # Display Generated Chapters
    if st.session_state.full_report_chapters:
        chapters = st.session_state.full_report_chapters

        # Chapter tabs
        chapter_titles = {
            "bab_1": "📖 Bab I - Pendahuluan",
            "bab_2": "📚 Bab II - Tinjauan Pustaka",
            "bab_3": "🔬 Bab III - Metodologi",
            "bab_4": "📊 Bab IV - Hasil & Pembahasan",
            "bab_5": "🎯 Bab V - Kesimpulan"
        }

        available_tabs = []
        available_keys = []
        for key, chapter in chapters.items():
            key_str = key.value if hasattr(key, 'value') else str(key)
            tab_name = chapter_titles.get(key_str, key_str)
            available_tabs.append(tab_name)
            available_keys.append(key)

        if available_tabs:
            tabs = st.tabs(available_tabs)

            for tab, key in zip(tabs, available_keys):
                with tab:
                    chapter = chapters[key]
                    st.markdown(f"## {chapter.title}")
                    st.markdown(chapter.content)
                    st.caption(f"📝 Word count: {chapter.word_count}")

        # Download Section
        st.markdown("""
        <div class="download-section">
            <h3>📥 Download Your Research Report</h3>
            <p style="color: var(--slate-400);">Export your complete systematic literature review in your preferred format</p>
        </div>
        """, unsafe_allow_html=True)

        # Get bibliography
        bibliography = []
        if st.session_state.slr_state:
            papers = st.session_state.slr_state.get("synthesis_ready", [])
            for p in papers:
                authors = p.get("authors", ["Unknown"])
                if isinstance(authors, list):
                    author_str = authors[0] if authors else "Unknown"
                else:
                    author_str = str(authors)
                year = p.get("year", "n.d.")
                title = p.get("title", "Untitled")
                source = p.get("source_title", p.get("journal", ""))
                doi = p.get("doi", "")
                ref = f"{author_str} ({year}). {title}. {source}."
                if doi:
                    ref += f" https://doi.org/{doi}"
                bibliography.append(ref)

        st.session_state.generated_bibliography = bibliography

        download_cols = st.columns(4)

        with download_cols[0]:
            md_report = st.session_state.report_orchestrator.export_to_markdown()
            st.download_button(
                label="📄 Markdown",
                data=md_report,
                file_name="muezza_research_report.md",
                mime="text/markdown",
                width="stretch"
            )

        with download_cols[1]:
            word_btn = st.button("📝 Word (Simple)", width="stretch")

            if word_btn:
                try:
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                        tmp_path = tmp.name

                    success = st.session_state.report_orchestrator.export_to_word(tmp_path)

                    if success:
                        with open(tmp_path, "rb") as f:
                            word_data = f.read()

                        st.download_button(
                            label="⬇️ Download",
                            data=word_data,
                            file_name="muezza_research_report.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            width="stretch"
                        )
                        os.unlink(tmp_path)
                except Exception as e:
                    st.error(f"Error: {str(e)}")

        with download_cols[2]:
            word_pro_btn = st.button("📑 Word (Pro)", width="stretch")

            if word_pro_btn:
                try:
                    import tempfile

                    chapters_dict = {}
                    for chapter_type, chapter in st.session_state.full_report_chapters.items():
                        key = chapter_type.value if hasattr(chapter_type, 'value') else str(chapter_type)
                        key_map = {
                            "bab_1": "BAB_I_PENDAHULUAN",
                            "bab_2": "BAB_II_TINJAUAN_PUSTAKA",
                            "bab_3": "BAB_III_METODOLOGI",
                            "bab_4": "BAB_IV_HASIL_PEMBAHASAN",
                            "bab_5": "BAB_V_KESIMPULAN"
                        }
                        formatted_key = key_map.get(key, key)
                        chapters_dict[formatted_key] = chapter.content

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                        tmp_path = tmp.name

                    generator = DocxGenerator(
                        researcher_name=st.session_state.researcher_name,
                        institution=st.session_state.institution
                    )

                    generator.generate_report(
                        chapters=chapters_dict,
                        bibliography=st.session_state.generated_bibliography,
                        filename=tmp_path,
                        title="LAPORAN SYSTEMATIC LITERATURE REVIEW",
                        include_title_page=True
                    )

                    with open(tmp_path, "rb") as f:
                        word_data = f.read()

                    st.download_button(
                        label="⬇️ Download Pro",
                        data=word_data,
                        file_name=f"Muezza_SLR_{st.session_state.researcher_name.replace(' ', '_')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        width="stretch"
                    )
                    os.unlink(tmp_path)

                except Exception as e:
                    st.error(f"Error: {str(e)}")

        with download_cols[3]:
            json_report = json.dumps({
                "metadata": {
                    "researcher": st.session_state.researcher_name,
                    "institution": st.session_state.institution,
                    "generated_at": datetime.now().isoformat(),
                    "tool": f"{APP_INFO['name']} v{APP_INFO['version']}",
                    "developer": APP_INFO['author'],
                    "github": APP_INFO['github']
                },
                "prisma_stats": {
                    "identified": st.session_state.prisma_stats.identified,
                    "included": st.session_state.prisma_stats.included_synthesis,
                },
                "bibliography_count": len(bibliography)
            }, indent=2)

            st.download_button(
                label="📋 Metadata",
                data=json_report,
                file_name="muezza_metadata.json",
                mime="application/json",
                width="stretch"
            )

    # ========== FOOTER ==========
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; padding: 2rem; color: var(--slate-500);">
        <p style="font-size: 1.5rem; margin-bottom: 0.5rem;">🐱</p>
        <p style="font-weight: 600; color: var(--emerald-400);">{APP_INFO['name']}</p>
        <p style="font-size: 0.85rem;">{APP_INFO['tagline']}</p>
        <p style="font-size: 0.75rem; margin-top: 1rem; color: var(--slate-600);">
            Built with LangGraph • ChromaDB • Claude AI • Streamlit
        </p>
        <p style="font-size: 0.7rem; color: var(--slate-600); font-style: italic;">
            "Precision in Research, Integrity in Every Citation"
        </p>
        <div style="margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid var(--slate-700);">
            <p style="font-size: 0.75rem; color: var(--slate-500);">
                <span style="color: var(--gold-400);">v{APP_INFO['version']}</span> •
                Developed by <a href="{APP_INFO['github']}" target="_blank" style="color: var(--emerald-400); text-decoration: none;">{APP_INFO['author']}</a>
            </p>
            <p style="font-size: 0.65rem; color: var(--slate-600); margin-top: 0.25rem;">
                Released: {APP_INFO['release_date']} •
                <a href="{APP_INFO['github']}" target="_blank" style="color: var(--slate-500); text-decoration: none;">GitHub Repository</a>
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

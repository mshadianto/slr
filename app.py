import streamlit as st

st.set_page_config(
    page_title="Muezza AI",
    page_icon="🐱",
    layout="wide"
)

st.title("🐱 Muezza AI")
st.subheader("Faithful Research Companion")

st.success("✅ App is running!")

st.write("---")
st.write("Environment check:")

import os
st.write(f"- PORT: {os.environ.get('PORT', 'not set')}")
st.write(f"- ANTHROPIC_API_KEY: {'✅ set' if os.environ.get('ANTHROPIC_API_KEY') else '❌ not set'}")
st.write(f"- SCOPUS_API_KEY: {'✅ set' if os.environ.get('SCOPUS_API_KEY') else '❌ not set'}")

st.write("---")
st.info("This is a minimal test version. Full app coming soon!")

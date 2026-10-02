import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="ResearchAI",
    page_icon="🔬",
    layout="wide"
)

st.title("ResearchAI — Multi Agent Research Assistant")
st.caption("4 AI agents collaborate to research any topic")

# Input
topic = st.text_input(
    "Enter a topic to research",
    placeholder="e.g. Artificial Intelligence trends in 2025"
)

if st.button("Start Research", type="primary"):
    if topic:
        with st.spinner("4 agents working... please wait"):
            res = requests.post(
                f"{API_URL}/research",
                json={"topic": topic}
            )

            if res.status_code == 200:
                data = res.json()
                st.session_state["result"] = data
            else:
                st.error("Something went wrong")
    else:
        st.warning("Please enter a topic")

# Results
if "result" in st.session_state:
    data = st.session_state["result"]

    st.success("Research complete!")

    tab1, tab2, tab3, tab4 = st.tabs([
        "Research",
        "Analysis", 
        "Draft Report",
        "Final Report"
    ])

    with tab1:
        st.subheader("Agent 1 — Researcher")
        st.write(data["research"])

    with tab2:
        st.subheader("Agent 2 — Analyzer")
        st.write(data["analysis"])

    with tab3:
        st.subheader("Agent 3 — Writer")
        st.write(data["report"])

    with tab4:
        st.subheader("Agent 4 — Reviewer (Final)")
        st.write(data["final_report"])

        st.divider()
        st.download_button(
            label="Download Report",
            data=data["final_report"],
            file_name=f"{data['topic'][:30]}_report.txt",
            mime="text/plain"
        )
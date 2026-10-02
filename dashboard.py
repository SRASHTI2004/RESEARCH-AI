import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="ResearchAI — Company Research Brief",
    page_icon="🔬",
    layout="wide"
)

st.title("ResearchAI — Company Research Brief")
st.caption("Enter a company name to get a sourced brief: overview, recent news, tech stack, interview prep")
st.info(
    "This Streamlit page is a temporary dev UI — a React + TypeScript "
    "frontend replaces it in a later phase.",
    icon="ℹ️",
)

# Input
company = st.text_input(
    "Company name",
    placeholder="e.g. Razorpay"
)

if st.button("Generate Brief", type="primary"):
    if company:
        with st.spinner("Searching the web and running 4 agents... this can take a minute"):
            try:
                res = requests.post(
                    f"{API_URL}/research",
                    json={"company": company},
                    timeout=120,
                )
            except requests.RequestException as exc:
                st.error(f"Could not reach the API: {exc}")
            else:
                if res.status_code == 200:
                    st.session_state["result"] = res.json()
                else:
                    detail = res.json().get("detail", res.text) if res.headers.get("content-type", "").startswith("application/json") else res.text
                    st.error(f"Something went wrong ({res.status_code}): {detail}")
    else:
        st.warning("Please enter a company name")

# Results
if "result" in st.session_state:
    data = st.session_state["result"]

    st.success("Brief complete!")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Research",
        "Analysis",
        "Draft Report",
        "Final Report",
        "Sources",
    ])

    with tab1:
        st.subheader("Agent 1 — Researcher (web search + synthesis)")
        st.write(data["research"])

    with tab2:
        st.subheader("Agent 2 — Analyzer")
        st.write(data["analysis"])

    with tab3:
        st.subheader("Agent 3 — Writer")
        st.write(data["report"])

    with tab4:
        st.subheader("Agent 4 — Reviewer (Final, fact-checked)")
        st.write(data["final_report"])

        st.divider()
        st.download_button(
            label="Download Report",
            data=data["final_report"],
            file_name=f"{data['company'][:30]}_brief.txt",
            mime="text/plain"
        )

    with tab5:
        st.subheader("Sources used")
        for source in data["sources"]:
            st.markdown(f"**[{source['index']}] {source['title']}**  \n{source['url']}  \n{source['snippet']}")

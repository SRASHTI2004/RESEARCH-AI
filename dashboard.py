import time

import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"
POLL_INTERVAL_SECONDS = 2
POLL_TIMEOUT_SECONDS = 180

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


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {st.session_state['access_token']}"}


# --- Login / register ---
if "access_token" not in st.session_state:
    st.subheader("Sign in")
    tab_login, tab_register = st.tabs(["Log in", "Register"])

    with tab_login:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Log in"):
            res = requests.post(f"{API_URL}/auth/login", json={"email": email, "password": password})
            if res.status_code == 200:
                st.session_state["access_token"] = res.json()["access_token"]
                st.rerun()
            else:
                st.error(res.json().get("detail", "Login failed"))

    with tab_register:
        reg_email = st.text_input("Email", key="register_email")
        reg_password = st.text_input("Password (min 8 chars)", type="password", key="register_password")
        if st.button("Register"):
            res = requests.post(f"{API_URL}/auth/register", json={"email": reg_email, "password": reg_password})
            if res.status_code == 201:
                st.success("Registered — switch to the Log in tab.")
            else:
                st.error(res.json().get("detail", "Registration failed"))

    st.stop()

st.success(f"Signed in", icon="✅")
if st.button("Log out"):
    del st.session_state["access_token"]
    st.rerun()

# --- Input ---
company = st.text_input(
    "Company name",
    placeholder="e.g. Razorpay"
)

if st.button("Generate Brief", type="primary"):
    if not company:
        st.warning("Please enter a company name")
    else:
        with st.spinner("Searching the web and running 4 agents... this can take a minute"):
            try:
                create_res = requests.post(
                    f"{API_URL}/research",
                    json={"company": company},
                    headers=_auth_headers(),
                    timeout=30,
                )
            except requests.RequestException as exc:
                st.error(f"Could not reach the API: {exc}")
                create_res = None

            if create_res is not None:
                if create_res.status_code == 401:
                    st.error("Session expired — please log in again.")
                    del st.session_state["access_token"]
                    st.rerun()
                elif create_res.status_code != 202:
                    st.error(f"Something went wrong ({create_res.status_code}): {create_res.text}")
                else:
                    job = create_res.json()
                    # POST returns 202 immediately with status="pending" (or
                    # already final under the eager-mode dev fallback — see
                    # docs/DECISIONS.md Phase 5) — poll until it settles.
                    deadline = time.time() + POLL_TIMEOUT_SECONDS
                    while job["status"] not in ("done", "failed") and time.time() < deadline:
                        time.sleep(POLL_INTERVAL_SECONDS)
                        job = requests.get(f"{API_URL}/research/{job['id']}", headers=_auth_headers()).json()

                    if job["status"] == "done":
                        st.session_state["result"] = job
                    elif job["status"] == "failed":
                        st.error(f"Research failed: {job.get('error')}")
                    else:
                        st.warning("Still running — refresh or check the History tab shortly.")

# --- Results ---
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

# --- History ---
st.divider()
st.subheader("History")
history_res = requests.get(f"{API_URL}/research", headers=_auth_headers())
if history_res.status_code == 200:
    jobs = history_res.json()
    if not jobs:
        st.caption("No research jobs yet.")
    for job in jobs:
        st.markdown(f"- **{job['company']}** — {job['status']} ({job['created_at']})")

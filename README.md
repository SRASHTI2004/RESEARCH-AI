# ResearchAI 🔬

A multi-agent AI research tool that searches the live internet, analyzes data, writes a structured report, and self-improves it — all automatically.

Built with LangGraph, Groq, Tavily, FastAPI, and Streamlit.

---

## How it works

You enter any topic. Then 4 AI agents take over:

| Agent | Job |
|-------|-----|
| Researcher | Searches the live internet using Tavily |
| Analyzer | Extracts insights, patterns, SWOT analysis |
| Writer | Writes a 7-section professional report |
| Reviewer | Scores the report, sends back if quality < 7/10 |

The reviewer creates a feedback loop — if the report scores below 7/10, it automatically goes back to the writer for improvement.

---

## Demo

> Enter any topic → get a full research report in minutes

Example topics tried:
- AI agents in 2026
- EV battery technology
- Quantum computing breakthroughs
- Climate tech funding

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| LangGraph | Agent orchestration + feedback loop |
| Groq (Llama 3.3 70B) | LLM for all agents |
| Tavily | Real-time web search |
| FastAPI | REST API backend |
| Streamlit | Frontend UI |

---

## What makes this different

- **Real web search** — agents search the actual internet, not just LLM memory
- **Feedback loop** — reviewer scores quality 1-10 and auto-improves if needed
- **Source tracking** — every web source used is shown in the UI
- **Export** — download final report as .txt or .md

---

## Project Structure

research-ai/
├── app/
│   ├── agents/
│   │   ├── researcher.py
│   │   ├── analyzer.py
│   │   ├── writer.py
│   │   └── reviewer.py
│   ├── tools/
│   │   └── search.py
│   ├── config.py
│   └── graph.py
├── main.py
├── streamlit_app.py
├── requirements.txt
└── .env.example


---

## Setup & Run

### 1. Clone the repo
```bash
git clone https://github.com/your-username/research-ai.git
cd research-ai
```

### 2. Create virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Add API keys
```bash
cp .env.example .env
```
Open `.env` and add your keys:

GROQ_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here

Get free keys here:
- Groq → https://console.groq.com
- Tavily → https://app.tavily.com

### 5. Run the app

Terminal 1 — Backend:
```bash
uvicorn main:app --reload
```

Terminal 2 — Frontend:
```bash
streamlit run streamlit_app.py
```

Open browser → http://localhost:8501

---

## Built by

Srashti — [@SRASHTI2004](https://github.com/SRASHTI2004)
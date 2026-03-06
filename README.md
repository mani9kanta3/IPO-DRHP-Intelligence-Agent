# 📊 IPO DRHP Intelligence Agent

> AI-powered Indian IPO analysis system using LangGraph multi-agent architecture. Upload any SEBI DRHP PDF and get a complete investor report with BUY/AVOID/WATCH verdict in under 2 minutes.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Click%20Here-blue)](http://40.192.105.49:8501)
[![GitHub](https://img.shields.io/badge/GitHub-Mani9kanta3-black)](https://github.com/Mani9kanta3/IPO-DRHP-Intelligence-Agent)

🚀 **[Live Demo](http://40.192.105.49:8501)** | 📂 **[GitHub](https://github.com/Mani9kanta3/IPO-DRHP-Intelligence-Agent)**

---

## 🎯 What This Does

Every year, millions of retail investors in India apply blindly to IPOs without understanding the company. A DRHP (Draft Red Herring Prospectus) is a 300–600 page legal document that contains everything an investor needs to know — but takes 3–4 days of expert time to analyze.

This system deploys **6 specialized AI agents** orchestrated through **LangGraph** that automatically:

- 📄 Parse and extract text + tables from 300–600 page DRHP PDFs
- 🚨 Detect financial red flags (promoter pledging, losses, concentration risks)
- 💰 Calculate 10+ financial ratios (CAGR, EBITDA margin, D/E ratio, ROE)
- 👤 Check promoter backgrounds using live web search
- 📈 Assess IPO valuation vs sector peers
- 📋 Generate plain-English investor report with **BUY / AVOID / WATCH** verdict
- 💡 Provide actionable investor guide (listing day strategy, long-term view, alternatives)

---

## 🏗️ System Architecture

```
User uploads DRHP PDF
        ↓
FastAPI Backend (/analyze)
        ↓
PDF Extraction (PyPDF2 + pdfplumber)
        ↓
Text Chunking (LangChain, 2000 tokens, 200 overlap)
        ↓
Vector Embedding (Gemini + ChromaDB)
        ↓
LangGraph StateGraph
        ↓
Agent 1: Section Identifier (keyword classification)
        ↓
┌──────────────────────────────────┐
│  PARALLEL EXECUTION              │
│  Agent 2: Red Flag Detector      │
│  Agent 3: Financial Health       │
│  Agent 4: Promoter Background    │
└──────────────────────────────────┘
        ↓
Agent 5: Valuation
        ↓
Agent 6: Report Writer
        ↓
Quality Checker (revision loop, max 2x)
        ↓
Streamlit Dashboard (report + charts)
```

---

## 🤖 6 Agents — What Each Does

| Agent | Name | Task | Model |
|-------|------|------|-------|
| 1 | Section Identifier | Classifies 270+ chunks into sections using keyword matching | No LLM (instant) |
| 2 | Red Flag Detector | Extracts CRITICAL/MODERATE/MINOR risks with severity scores | Gemini 2.5 Flash |
| 3 | Financial Health | Extracts 3-year financials, calculates 10+ ratios via Pandas | Gemini 2.5 Flash |
| 4 | Promoter Background | Web searches each promoter for fraud/SEBI/court cases | Gemini 2.5 Flash + Tavily |
| 5 | Valuation | Compares IPO P/E vs sector peers, gives EXPENSIVE/FAIR/CHEAP | Gemini 2.5 Flash + Tavily |
| 6 | Report Writer | Synthesizes all outputs into plain-English investor report | Gemini 2.5 Flash |

---

## 🛠️ Tech Stack

| Category | Technology |
|----------|-----------|
| Agent Orchestration | LangGraph 0.2.x |
| LLM Framework | LangChain 0.3.x |
| LLM Provider | Google Gemini 2.5 Flash |
| Embeddings | Gemini Embedding 001 |
| Vector Database | ChromaDB (local) |
| PDF Processing | PyPDF2 + pdfplumber |
| Web Search | Tavily Search API |
| Data Processing | Pandas + NumPy |
| Backend API | FastAPI + Uvicorn |
| Frontend | Streamlit + Plotly |
| Security | API Key Authentication |
| Containerization | Docker + Docker Compose |
| Cloud | AWS EC2 |
| CI/CD | GitHub Actions |

---

## ⚡ Performance

| Metric | Value |
|--------|-------|
| Analysis time (first run) | ~2 minutes |
| Analysis time (cached PDF) | ~100 seconds |
| DRHP pages supported | 300–700 pages |
| Agents running in parallel | 3 (Agents 2, 3, 4) |
| Speed improvement | 4.2x (424s → 100s) |
| Cost per analysis | ~₹0 (Gemini free tier) |

---

## 📁 Project Structure

```
ipo-drhp-agent/
├── src/
│   ├── ingestion/
│   │   ├── pdf_loader.py       # PyPDF2 + pdfplumber extraction
│   │   ├── chunker.py          # LangChain text splitting
│   │   └── embedder.py         # Gemini embeddings + ChromaDB
│   ├── agents/
│   │   ├── state.py            # LangGraph ResearchState TypedDict
│   │   ├── supervisor.py       # Agent 1: Section Identifier
│   │   ├── red_flag.py         # Agent 2: Red Flag Detector
│   │   ├── financial.py        # Agent 3: Financial Health
│   │   ├── promoter.py         # Agent 4: Promoter Background
│   │   ├── valuation.py        # Agent 5: Valuation
│   │   └── reporter.py         # Agent 6: Report Writer
│   ├── graph/
│   │   └── workflow.py         # LangGraph StateGraph + parallel execution
│   ├── api/
│   │   ├── main.py             # FastAPI endpoints
│   │   └── schemas.py          # Pydantic models
│   └── frontend/
│       └── app.py              # Streamlit dashboard
├── prompts/
│   ├── red_flag_prompt.txt
│   ├── financial_prompt.txt
│   └── report_prompt.txt
├── configs/
│   └── config.yaml
├── data/
│   └── sample_drhps/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env
```

---

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/Mani9kanta3/IPO-DRHP-Intelligence-Agent.git
cd IPO-DRHP-Intelligence-Agent
python -m venv venv
venv\Scripts\activate       # Windows
source venv/bin/activate    # Mac/Linux
pip install -r requirements.txt
```

### 2. Configure API Keys

Create `.env` file:

```env
GOOGLE_API_KEY=your-gemini-api-key
TAVILY_API_KEY=tvly-your-tavily-key
API_KEY=drhp-secret-key-2024
```

Get your keys:
- **Gemini**: [aistudio.google.com](https://aistudio.google.com) → Get API Key (free)
- **Tavily**: [tavily.com](https://tavily.com) → Sign up (1000 searches/month free)

### 3. Run with Docker

```bash
docker-compose up --build
```

Open browser: `http://localhost:8501`

### 4. Run Locally (without Docker)

Terminal 1 — Start API:
```bash
uvicorn src.api.main:app --port 8000
```

Terminal 2 — Start Dashboard:
```bash
streamlit run src/frontend/app.py
```

### 5. Upload a DRHP

Download any DRHP PDF from [SEBI website](https://www.sebi.gov.in) and upload it.

---

## 📊 Sample Output

```
DRHP ANALYSIS REPORT — SWIGGY LIMITED
Verdict: 🔴 AVOID

FINANCIAL HEALTH: 4/10
  Revenue FY24: ₹116,343 million
  PAT FY24: -₹23,502 million (LOSS)
  Revenue CAGR: 37.88% (STRONG)
  PAT Margin: -20.2% (CONCERN)

RED FLAGS: 2 Critical | 8 Moderate | 3 Minor
  🔴 [CRITICAL] Continuous Losses with No Profitability Timeline
  🔴 [CRITICAL] Material Subsidiary Incurring Continuous Losses
  🟠 [MODERATE] Pending Licenses for Dark Stores
  ...

PROMOTER CHECK:
  🟡 Sriharsha Majety — YELLOW
  🟢 Rahul Bothra — GREEN
  ...

VALUATION: EXPENSIVE
  Loss-making company — P/E not applicable
  Food delivery peers (Zomato) trade at 55x P/E

INVESTOR ACTION GUIDE:
  Should I apply? No — continuous losses + expensive valuation
  Short-term: Avoid applying
  Long-term: Wait for 2 profitable quarters
  Risk vs FD: Very High
```

---

## 🔌 API Reference

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | System health check |
| `/analyze` | POST | Yes | Upload PDF, start analysis |
| `/status/{job_id}` | GET | No | Check analysis progress |
| `/report/{job_id}` | GET | Yes | Get complete report JSON |

### Authentication

Add header to protected requests:
```
X-API-Key: your-api-key
```

### Example

```python
import requests

# Upload DRHP
with open("swiggy_drhp.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/analyze",
        files={"file": f},
        headers={"X-API-Key": "your-key"}
    )
job_id = response.json()["job_id"]

# Poll status
import time
while True:
    status = requests.get(f"http://localhost:8000/status/{job_id}").json()
    if status["status"] == "complete":
        break
    time.sleep(5)

# Get report
report = requests.get(
    f"http://localhost:8000/report/{job_id}",
    headers={"X-API-Key": "your-key"}
).json()
print(report["verdict"])  # BUY / AVOID / WATCH
```

---

## 🧪 Tested DRHPs

| Company | Verdict | Key Findings |
|---------|---------|-------------|
| Swiggy (2024) | AVOID | Continuous losses, no promoter lock-in |
| Ola Electric (2024) | AVOID | FAME subsidy dependency, promoter SEBI warning |

---

## ⚠️ Important Disclaimer

**This system generates AI-powered educational analysis only. It does NOT constitute investment advice.**

- Analysis is based solely on publicly available DRHP documents
- AI models can make errors in extraction and interpretation
- Always consult a SEBI-registered investment advisor before investing
- Past IPO performance does not guarantee future results

---

## 🔮 Future Improvements

- [ ] Grey Market Premium (GMP) integration
- [ ] IPO subscription data tracking
- [ ] Post-listing performance tracker (did BUY/AVOID verdict prove correct?)
- [ ] Side-by-side comparison of two DRHPs
- [ ] OCR support for scanned DRHP pages
- [ ] Historical IPO database

---

## 👨‍💻 Author

Built by **Manikanta Pudi**

- Portfolio: [manikantapudi.com](https://manikantapudi.com)
- GitHub: [github.com/Mani9kanta3](https://github.com/Mani9kanta3)
- LinkedIn: [linkedin.com/in/manikantapudi](https://linkedin.com/in/manikantapudi)

---

*Built with LangGraph, LangChain, Google Gemini, ChromaDB, FastAPI, Streamlit, Docker, and AWS EC2*
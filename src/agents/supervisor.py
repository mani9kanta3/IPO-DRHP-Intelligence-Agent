import json
from src.agents.state import ResearchState
from src.agents.llm import get_llm
from src.ingestion.embedder import search


# Keyword-based fast classification
SECTION_KEYWORDS = {
    "risk_factors": [
        "risk", "risks", "threat", "uncertainty", "adverse", "failure",
        "litigation", "penalty", "regulatory", "compliance", "lawsuit",
        "legal proceedings", "contingent", "hazard"
    ],
    "financials": [
        "revenue", "profit", "loss", "ebitda", "balance sheet", "cash flow",
        "income statement", "borrowings", "equity", "assets", "liabilities",
        "earnings per share", "eps", "pat", "ebit", "gross margin",
        "financial statements", "auditor", "ind as"
    ],
    "promoter": [
        "promoter", "founder", "director", "key managerial", "management",
        "chairman", "ceo", "cfo", "whole-time director", "shareholding pattern",
        "biography", "experience", "qualification"
    ],
    "litigation": [
        "litigation", "legal proceedings", "court", "tribunal", "arbitration",
        "criminal", "civil suit", "writ petition", "high court", "supreme court",
        "pending cases", "enforcement"
    ],
    "objects_of_issue": [
        "objects of", "use of proceeds", "utilization of funds", "fresh issue",
        "offer for sale", "net proceeds", "deployment of funds"
    ],
    "business_overview": [
        "our business", "overview", "industry", "market opportunity",
        "competitive strengths", "business model", "operations", "products",
        "services", "customers", "geographic"
    ]
}


def classify_by_keywords(text: str) -> str:
    """Fast keyword-based classification. Returns section name."""
    text_lower = text.lower()
    scores = {}

    for section, keywords in SECTION_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        scores[section] = score

    best = max(scores, key=scores.get)
    # If best score is 0 or tie is unclear, return "other"
    if scores[best] == 0:
        return "other"
    return best


def section_identifier_agent(state: ResearchState) -> ResearchState:
    print("\n[Agent 1] Section Identifier running...")

    pdf_hash = state.get("pdf_hash")

    sections = {
        "business_overview": [],
        "risk_factors": [],
        "financials": [],
        "promoter": [],
        "litigation": [],
        "objects_of_issue": [],
        "other": []
    }

    queries = [
        "business overview company description operations",
        "risk factors warnings threats challenges",
        "financial statements revenue profit loss balance sheet",
        "promoter management key people founders directors",
        "litigation legal proceedings court cases",
        "objects of issue use of funds proceeds"
    ]

    seen_chunk_ids = set()
    all_chunks = []

    for query in queries:
        results = search(query, top_k=50, pdf_hash=pdf_hash)
        for chunk in results:
            cid = chunk["metadata"]["chunk_id"]
            if cid not in seen_chunk_ids:
                seen_chunk_ids.add(cid)
                all_chunks.append(chunk)

    print(f"  Total unique chunks to classify: {len(all_chunks)}")

    for chunk in all_chunks:
        section = classify_by_keywords(chunk["content"])
        sections[section].append(chunk["content"])

    for section, chunks in sections.items():
        print(f"  {section}: {len(chunks)} chunks")

    state["sections"] = sections
    state["status"] = "sections_identified"
    return state

if __name__ == "__main__":
    from src.ingestion.pdf_loader import load_pdf
    from src.ingestion.embedder import get_pdf_hash

    result = load_pdf("data/sample_drhps/swiggy_drhp.pdf")
    pdf_hash = get_pdf_hash("data/sample_drhps/swiggy_drhp.pdf")

    state = ResearchState(
        drhp_text=result["text"],
        pdf_path="data/sample_drhps/swiggy_drhp.pdf",
        file_name=result["file_name"],
        total_pages=result["total_pages"],
        pdf_hash=pdf_hash,
        sections={},
        red_flags=[],
        risk_score=0,
        financials={},
        promoter_report=[],
        valuation={},
        final_report="",
        verdict="",
        revision_count=0,
        status="started",
        errors=[]
    )

    state = section_identifier_agent(state)
    print("\nDone!")
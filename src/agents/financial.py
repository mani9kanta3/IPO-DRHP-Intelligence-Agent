import json
import pandas as pd
from src.agents.state import ResearchState
from src.agents.llm import get_llm
from src.ingestion.embedder import search
from pathlib import Path


def load_prompt() -> str:
    return Path("prompts/financial_prompt.txt").read_text()


def calculate_ratios(data: dict) -> dict:
    """Calculate financial ratios using Pandas. Never use LLM for math."""
    ratios = {}
    try:
        fy22 = data.get("fy2022", {})
        fy23 = data.get("fy2023", {})
        fy24 = data.get("fy2024", {})

        rev22 = fy22.get("revenue")
        rev23 = fy23.get("revenue")
        rev24 = fy24.get("revenue")

        # Revenue CAGR (FY22 to FY24)
        if rev22 and rev24 and rev22 > 0:
            ratios["revenue_cagr"] = round(((rev24 / rev22) ** 0.5 - 1) * 100, 2)

        # PAT Margin FY24
        pat24 = fy24.get("pat")
        if pat24 and rev24 and rev24 > 0:
            ratios["pat_margin_fy24"] = round((pat24 / rev24) * 100, 2)

        # EBITDA Margin FY24
        ebitda24 = fy24.get("ebitda")
        if ebitda24 and rev24 and rev24 > 0:
            ratios["ebitda_margin_fy24"] = round((ebitda24 / rev24) * 100, 2)

        # Debt to Equity
        debt24 = fy24.get("total_debt")
        equity24 = fy24.get("equity")
        if debt24 is not None and equity24 and equity24 > 0:
            ratios["debt_to_equity"] = round(debt24 / equity24, 2)

        # Current Ratio
        ca24 = fy24.get("current_assets")
        cl24 = fy24.get("current_liabilities")
        if ca24 and cl24 and cl24 > 0:
            ratios["current_ratio"] = round(ca24 / cl24, 2)

        # Revenue growth FY23 to FY24
        if rev23 and rev24 and rev23 > 0:
            ratios["revenue_growth_fy24"] = round(((rev24 - rev23) / rev23) * 100, 2)

    except Exception as e:
        print(f"  Warning: ratio calculation error: {e}")

    return ratios


def score_financial_health(extracted: dict, ratios: dict) -> int:
    score = 0

    # Revenue CAGR > 20% → +2
    cagr = ratios.get("revenue_cagr", 0)
    if cagr and cagr > 20:
        score += 2
    elif cagr and cagr > 0:
        score += 1

    # Positive PAT → +2
    pat = extracted.get("fy2024", {}).get("pat")
    if pat and pat > 0:
        score += 2

    # Positive OCF → +2
    ocf = extracted.get("fy2024", {}).get("ocf")
    if ocf and ocf > 0:
        score += 2

    # D/E < 1 → +1
    de = ratios.get("debt_to_equity")
    if de is not None and de < 1:
        score += 1

    # Current ratio > 1 → +1
    cr = ratios.get("current_ratio")
    if cr and cr > 1:
        score += 1

    # EBITDA margin > 10% → +2
    em = ratios.get("ebitda_margin_fy24")
    if em and em > 10:
        score += 2
    elif em and em > 0:
        score += 1

    return min(score, 10)


def financial_agent(state: ResearchState) -> ResearchState:
    print("\n[Agent 3] Financial Health Agent running...")

    llm = get_llm(complex_task=True)

    # Get financial chunks
    fin_chunks = state["sections"].get("financials", [])

    # Targeted searches for financial data
    queries = [
        "total revenue income from operations",
        "profit after tax net loss",
        "EBITDA adjusted earnings",
        "total borrowings debt",
        "cash flow from operations",
        "earnings per share EPS",
        "current assets current liabilities"
    ]

    extra = []
    seen = set(fin_chunks)
    for q in queries:
        results = search(q, top_k=5)
        for r in results:
            if r["content"] not in seen:
                seen.add(r["content"])
                extra.append(r["content"])

    all_chunks = fin_chunks + extra
    print(f"  Analyzing {len(all_chunks)} chunks for financials...")

    context = "\n\n---\n\n".join(all_chunks[:30])
    prompt_template = load_prompt()

    prompt = f"""{prompt_template}

Here is the DRHP financial text:

{context}

Return ONLY valid JSON, no markdown."""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        extracted = json.loads(content)

        ratios = calculate_ratios(extracted)
        health_score = score_financial_health(extracted, ratios)

        print(f"  Currency unit: {extracted.get('currency_unit', 'unknown')}")
        print(f"  FY24 Revenue: {extracted.get('fy2024', {}).get('revenue')}")
        print(f"  FY24 PAT: {extracted.get('fy2024', {}).get('pat')}")
        print(f"  Revenue CAGR: {ratios.get('revenue_cagr')}%")
        print(f"  Financial Health Score: {health_score}/10")

        state["financials"] = {
            "extracted": extracted,
            "ratios": ratios,
            "health_score": health_score
        }
        state["status"] = "financials_analyzed"

    except Exception as e:
        print(f"  Error in financial analysis: {e}")
        state["errors"].append(f"Financial agent error: {str(e)}")
        state["financials"] = {"health_score": 5}

    return state


if __name__ == "__main__":
    from src.ingestion.pdf_loader import load_pdf
    from src.agents.supervisor import section_identifier_agent

    result = load_pdf("data/sample_drhps/swiggy_drhp.pdf")

    state = ResearchState(
        drhp_text=result["text"],
        pdf_path="data/sample_drhps/swiggy_drhp.pdf",
        file_name=result["file_name"],
        total_pages=result["total_pages"],
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
    state = financial_agent(state)

    print(f"\nFinancial Health Score: {state['financials']['health_score']}/10")
    print(f"Ratios: {state['financials'].get('ratios', {})}")
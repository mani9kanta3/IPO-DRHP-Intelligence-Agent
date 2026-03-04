import json
from src.agents.state import ResearchState
from src.agents.llm import get_llm
from src.ingestion.embedder import search
from tavily import TavilyClient
import os
from dotenv import load_dotenv

load_dotenv()


def extract_ipo_details(state: ResearchState, llm) -> dict:
    """Extract IPO price band, EPS, sector from DRHP."""
    queries = [
        "price band offer price per share",
        "earnings per share EPS face value",
        "industry sector business description"
    ]

    chunks = []
    seen = set()
    for q in queries:
        results = search(q, top_k=5)
        for r in results:
            if r["content"] not in seen:
                seen.add(r["content"])
                chunks.append(r["content"])

    context = "\n\n---\n\n".join(chunks[:15])

    prompt = f"""Extract IPO details from this DRHP text:

{context}

Return ONLY this JSON:
{{
  "company_name": "company name",
  "price_band_low": null,
  "price_band_high": null,
  "face_value": null,
  "eps_fy24": null,
  "sector": "food delivery / EV / fintech etc",
  "currency": "INR"
}}"""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except:
        return {}


def get_peer_valuations(sector: str, tavily: TavilyClient) -> list:
    """Search for listed peer companies and their P/E ratios."""
    queries = [
        f"{sector} listed companies India PE ratio 2024",
        f"{sector} NSE BSE listed stocks valuation multiple"
    ]

    peers = []
    for query in queries:
        try:
            results = tavily.search(query, max_results=3)
            for r in results["results"]:
                peers.append(r.get("content", "")[:400])
        except:
            pass

    return peers


def valuation_agent(state: ResearchState) -> ResearchState:
    print("\n[Agent 5] Valuation Agent running...")

    llm = get_llm(complex_task=True)
    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

    # Extract IPO details
    ipo_details = extract_ipo_details(state, llm)
    print(f"  Company: {ipo_details.get('company_name')}")
    print(f"  Price Band: ₹{ipo_details.get('price_band_low')} - ₹{ipo_details.get('price_band_high')}")
    print(f"  Sector: {ipo_details.get('sector')}")
    print(f"  EPS FY24: {ipo_details.get('eps_fy24')}")

    sector = ipo_details.get("sector", "technology")
    peer_data = get_peer_valuations(sector, tavily)
    peer_context = "\n\n".join(peer_data)

    # Get financial data from previous agent
    financials = state.get("financials", {})
    extracted = financials.get("extracted", {})
    fy24 = extracted.get("fy2024", {})
    revenue = fy24.get("revenue")
    pat = fy24.get("pat")

    price_high = ipo_details.get("price_band_high")
    eps = ipo_details.get("eps_fy24")

    # Calculate P/E if profitable
    issue_pe = None
    issue_ps = None

    if eps and eps > 0 and price_high:
        issue_pe = round(price_high / eps, 2)
    
    # Calculate P/S ratio (useful for loss-making companies)
    # Using market cap estimate (price * shares) / revenue is complex
    # Instead ask LLM to interpret from peer context

    prompt = f"""You are a valuation analyst for Indian IPOs.

Company: {ipo_details.get('company_name')}
Sector: {sector}
IPO Price Band: ₹{ipo_details.get('price_band_low')} - ₹{ipo_details.get('price_band_high')}
EPS FY24: {eps} (negative means loss-making)
Issue P/E: {issue_pe} (null if loss-making)
FY24 Revenue: {revenue} million INR
FY24 PAT: {pat} million INR

Peer company valuation data from web:
{peer_context}

Based on this, provide valuation assessment.

Return ONLY this JSON:
{{
  "issue_pe": {issue_pe},
  "sector_avg_pe": null,
  "is_loss_making": true/false,
  "valuation_call": "EXPENSIVE/FAIR/CHEAP",
  "premium_discount_pct": null,
  "reasoning": "2-3 sentence explanation",
  "peer_companies": ["list of peer companies mentioned"]
}}"""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip().replace("```json", "").replace("```", "").strip()
        valuation = json.loads(content)

        print(f"  Valuation Call: {valuation.get('valuation_call')}")
        print(f"  Issue P/E: {valuation.get('issue_pe')}")
        print(f"  Reasoning: {valuation.get('reasoning', '')[:100]}...")

        state["valuation"] = valuation
        state["status"] = "valuation_complete"

    except Exception as e:
        print(f"  Error in valuation: {e}")
        state["errors"].append(f"Valuation agent error: {str(e)}")
        state["valuation"] = {"valuation_call": "FAIR", "reasoning": "Could not determine valuation."}

    return state


if __name__ == "__main__":
    from src.ingestion.pdf_loader import load_pdf
    from src.agents.supervisor import section_identifier_agent
    from src.agents.financial import financial_agent

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
    state = valuation_agent(state)

    print(f"\nValuation: {state['valuation']}")
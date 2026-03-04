import json
from src.agents.state import ResearchState
from src.agents.llm import get_llm
from src.ingestion.embedder import search
from tavily import TavilyClient
import os
from dotenv import load_dotenv

load_dotenv()


def extract_promoter_names(state: ResearchState, llm) -> list:
    """Extract promoter/founder names from DRHP promoter section."""
    promoter_chunks = state["sections"].get("promoter", [])
    context = "\n\n---\n\n".join(promoter_chunks[:15])

    prompt = f"""From this DRHP text, extract the names of all promoters, founders, and key management people.

{context}

Return ONLY a JSON array of full names. Example: ["Sriharsha Majety", "Nandan Reddy"]
No explanation, just the JSON array."""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        names = json.loads(content)
        return names[:5]  # Max 5 people to control Tavily usage
    except:
        return []


def search_person_background(name: str, tavily: TavilyClient) -> list:
    """Run 4 targeted searches for a person."""
    queries = [
        f"{name} fraud controversy allegations",
        f"{name} SEBI action regulatory penalty India",
        f"{name} court case legal proceedings",
        f"{name} previous companies startup track record"
    ]

    results = []
    for query in queries:
        try:
            response = tavily.search(query, max_results=3)
            for r in response["results"]:
                results.append({
                    "query": query,
                    "title": r.get("title", ""),
                    "content": r.get("content", "")[:500]
                })
        except Exception as e:
            print(f"    Search failed for '{query}': {e}")

    return results


def rate_promoter(name: str, search_results: list, llm) -> dict:
    """Use LLM to rate a promoter based on search results."""
    results_text = ""
    for r in search_results:
        results_text += f"\nTitle: {r['title']}\nContent: {r['content']}\n---"

    prompt = f"""You are doing background check on {name}, a promoter/founder of an Indian company filing for IPO.

Based on these web search results:
{results_text}

Rate this person as:
- GREEN: Clean background, no serious concerns
- YELLOW: Some concerns worth monitoring (aggressive style, minor disputes)
- RED: Serious issues (SEBI actions, fraud allegations, major litigation)

Return ONLY this JSON:
{{
  "name": "{name}",
  "rating": "GREEN/YELLOW/RED",
  "key_findings": "2-3 sentence summary of what was found",
  "concerns": ["list of specific concerns if any"]
}}"""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        return {
            "name": name,
            "rating": "YELLOW",
            "key_findings": "Could not retrieve background information.",
            "concerns": []
        }


def promoter_agent(state: ResearchState) -> ResearchState:
    print("\n[Agent 4] Promoter Background Agent running...")

    llm = get_llm(complex_task=True)
    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

    # Extract promoter names from DRHP
    names = extract_promoter_names(state, llm)
    print(f"  Found promoters/key people: {names}")

    if not names:
        print("  No promoter names found — marking as unknown")
        state["promoter_report"] = [{"name": "Unknown", "rating": "YELLOW", "key_findings": "No identifiable promoter found in DRHP.", "concerns": []}]
        state["status"] = "promoters_checked"
        return state

    promoter_reports = []
    for name in names:
        print(f"  Searching background for: {name}")
        search_results = search_person_background(name, tavily)
        report = rate_promoter(name, search_results, llm)
        promoter_reports.append(report)
        print(f"    Rating: {report['rating']} — {report['key_findings'][:80]}...")

    state["promoter_report"] = promoter_reports
    state["status"] = "promoters_checked"
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
    state = promoter_agent(state)

    print(f"\nPromoter Reports:")
    for p in state["promoter_report"]:
        print(f"  {p['name']}: {p['rating']} — {p['key_findings']}")
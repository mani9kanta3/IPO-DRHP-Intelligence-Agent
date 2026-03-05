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
        return names[:5]
    except:
        return []


def extract_company_name(state: ResearchState, llm) -> str:
    """Extract company name by fetching cover page chunk directly."""
    pdf_hash = state.get("pdf_hash")
    
    if not pdf_hash:
        print("  Warning: no pdf_hash in state")
        return "the company"

    try:
        from src.ingestion.embedder import get_chroma_client
        client = get_chroma_client()
        col = client.get_collection('drhp_chunks')

        cover_ids = [f"{pdf_hash}_0", f"{pdf_hash}_1"]
        results = col.get(ids=cover_ids)

        if not results['documents']:
            print("  Warning: no cover page chunks found")
            return "the company"

        cover_text = "\n".join(results['documents'])

        prompt = f"""Extract only the main company name ending with 'Limited' from this DRHP cover page.
Examples: 'Swiggy Limited', 'Ola Electric Mobility Limited'

Text: {cover_text[:600]}

Return ONLY the company name. Nothing else."""

        resp = llm.invoke(prompt)
        candidate = resp.content.strip().split("\n")[0].strip()
        candidate = candidate.replace('"', '').replace("'", '').strip()

        if (
            "limited" in candidate.lower()
            and len(candidate) < 80
            and "not" not in candidate.lower()
            and "unknown" not in candidate.lower()
        ):
            print(f"  Company identified: {candidate}")
            return candidate
        else:
            print(f"  Warning: rejected candidate '{candidate}'")

    except Exception as e:
        print(f"  Company name extraction error: {e}")

    return "the company"

def search_person_background(name: str, company: str, tavily: TavilyClient) -> list:
    """Run targeted searches for a person with company context."""
    queries = [
        f"{name} {company} SEBI fraud controversy India",
        f"{name} {company} court case legal proceedings",
        f"{name} founder CEO background track record India"
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
            print(f"    Search failed: {e}")

    return results


def rate_promoter(name: str, company: str, search_results: list, llm) -> dict:
    """Rate a promoter based on search results."""
    results_text = ""
    for r in search_results:
        results_text += f"\nTitle: {r['title']}\nContent: {r['content']}\n---"

    prompt = f"""You are doing a background check on {name}, associated with {company} which is filing for an IPO in India.

Based on these web search results:
{results_text}

IMPORTANT RULES:
1. Only rate RED if there is CLEAR evidence of serious issues directly related to THIS person
2. Do not confuse this person with someone else with a similar name
3. Family members (wife, parents) should only be rated based on their OWN actions
4. YELLOW = minor concerns or unverified allegations
5. GREEN = clean or no significant issues found

Rate this person:
- GREEN: Clean background, no serious concerns
- YELLOW: Some concerns worth monitoring
- RED: Serious verified issues (SEBI actions, fraud conviction, major litigation)

Return ONLY this JSON:
{{
  "name": "{name}",
  "rating": "GREEN/YELLOW/RED",
  "key_findings": "2-3 sentence summary",
  "concerns": ["specific concern 1", "specific concern 2"]
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
            "key_findings": "Could not retrieve sufficient background information.",
            "concerns": []
        }


def promoter_agent(state: ResearchState) -> ResearchState:
    print("\n[Agent 4] Promoter Background Agent running...")

    llm = get_llm(complex_task=True)
    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

    # Extract company name from document
    company_name = extract_company_name(state, llm)
    print(f"  Company identified: {company_name}")

    # Extract promoter names
    names = extract_promoter_names(state, llm)
    print(f"  Found promoters/key people: {names}")

    if not names:
        print("  No promoter names found")
        state["promoter_report"] = [{
            "name": "Unknown",
            "rating": "YELLOW",
            "key_findings": "No identifiable promoter found in DRHP.",
            "concerns": []
        }]
        state["status"] = "promoters_checked"
        return state

    import concurrent.futures

    def check_promoter(name):
        search_results = search_person_background(name, company_name, tavily)
        return rate_promoter(name, company_name, search_results, llm)

    promoter_reports = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(check_promoter, name): name for name in names}
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                report = future.result()
                promoter_reports.append(report)
                print(f"    {report['rating']} — {name}: {report['key_findings'][:80]}...")
            except Exception as e:
                print(f"    Failed for {name}: {e}")
                promoter_reports.append({
                    "name": name,
                    "rating": "YELLOW",
                    "key_findings": "Could not retrieve background.",
                    "concerns": []
                })

    state["promoter_report"] = promoter_reports
    state["status"] = "promoters_checked"
    return state

    pdf_hash = state.get("pdf_hash")
    # update company name search
    results = search("draft red herring prospectus limited IPO offer", top_k=3, pdf_hash=pdf_hash)


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
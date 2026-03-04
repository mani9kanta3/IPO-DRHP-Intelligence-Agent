import json
from src.agents.state import ResearchState
from src.agents.llm import get_llm
from src.ingestion.embedder import search
from pathlib import Path


def load_prompt() -> str:
    return Path("prompts/red_flag_prompt.txt").read_text()


def red_flag_agent(state: ResearchState) -> ResearchState:
    print("\n[Agent 2] Red Flag Detector running...")

    llm = get_llm(complex_task=True)

    # Get risk factor chunks from sections
    risk_chunks = state["sections"].get("risk_factors", [])

    # Also do targeted semantic searches for specific red flags
    targeted_queries = [
        "promoter shares pledged encumbered",
        "related party transactions",
        "customer concentration single client revenue",
        "negative cash flow losses accumulated deficit",
        "SEBI regulatory investigation penalty",
        "government subsidy dependency",
        "debt borrowings loan",
        "key man dependency single person"
    ]

    extra_chunks = []
    seen = set(risk_chunks)
    for query in targeted_queries:
        results = search(query, top_k=5)
        for r in results:
            if r["content"] not in seen:
                seen.add(r["content"])
                extra_chunks.append(r["content"])

    all_chunks = risk_chunks + extra_chunks
    print(f"  Analyzing {len(all_chunks)} chunks for red flags...")

    # Combine chunks into context (limit to avoid token overflow)
    context = "\n\n---\n\n".join(all_chunks[:40])

    prompt_template = load_prompt()

    prompt = f"""{prompt_template}

Here is the DRHP text to analyze:

{context}

Remember: Return ONLY valid JSON, no markdown, no explanation."""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        result = json.loads(content)

        red_flags = result.get("red_flags", [])
        risk_score = result.get("overall_risk_score", 5)
        risk_summary = result.get("risk_summary", "")

        print(f"  Red flags found: {len(red_flags)}")
        for flag in red_flags:
            print(f"  [{flag['severity']}] {flag['flag']}")

        state["red_flags"] = red_flags
        state["risk_score"] = risk_score
        state["status"] = "red_flags_detected"

    except Exception as e:
        print(f"  Error in red flag detection: {e}")
        state["errors"].append(f"Red flag agent error: {str(e)}")
        state["red_flags"] = []
        state["risk_score"] = 5

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
    state = red_flag_agent(state)

    print(f"\nRisk Score: {state['risk_score']}/10")
    print(f"Total Red Flags: {len(state['red_flags'])}")
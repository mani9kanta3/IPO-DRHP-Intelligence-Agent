import json
from src.agents.state import ResearchState
from src.agents.llm import get_llm
from pathlib import Path


def load_prompt() -> str:
    return Path("prompts/report_prompt.txt").read_text()


def determine_verdict(state: ResearchState) -> str:
    risk_score = state.get("risk_score", 5)
    health_score = state.get("financials", {}).get("health_score", 5)
    valuation_call = state.get("valuation", {}).get("valuation_call", "FAIR")
    is_loss_making = state.get("valuation", {}).get("is_loss_making", False)
    promoter_ratings = [p.get("rating", "YELLOW") for p in state.get("promoter_report", [])]

    has_red_promoter = "RED" in promoter_ratings

    if has_red_promoter or (valuation_call == "EXPENSIVE" and is_loss_making) or risk_score >= 7 or health_score <= 3:
        return "AVOID"
    elif risk_score <= 4 and health_score >= 7 and valuation_call != "EXPENSIVE" and not has_red_promoter:
        return "BUY"
    else:
        return "WATCH"


def report_writer_agent(state: ResearchState) -> ResearchState:
    print("\n[Agent 6] Report Writer running...")

    llm = get_llm(complex_task=True)
    verdict = determine_verdict(state)

    # Prepare summary data for the LLM
    red_flags_summary = []
    for f in state.get("red_flags", []):
        red_flags_summary.append({
            "flag": f.get("flag"),
            "severity": f.get("severity"),
            "plain_english": f.get("plain_english", "")[:200]
        })

    financials = state.get("financials", {})
    ratios = financials.get("ratios", {})
    extracted = financials.get("extracted", {})
    fy24 = extracted.get("fy2024", {})

    promoter_summary = []
    for p in state.get("promoter_report", []):
        promoter_summary.append({
            "name": p.get("name"),
            "rating": p.get("rating"),
            "key_findings": p.get("key_findings", "")[:200]
        })

    data = {
        "company": state.get("file_name", "").replace("_drhp.pdf", "").upper(),
        "total_pages": state.get("total_pages"),
        "verdict": verdict,
        "risk_score": state.get("risk_score"),
        "red_flags": red_flags_summary,
        "financial_health_score": financials.get("health_score"),
        "fy24_revenue_million": fy24.get("revenue"),
        "fy24_pat_million": fy24.get("pat"),
        "revenue_cagr": ratios.get("revenue_cagr"),
        "pat_margin": ratios.get("pat_margin_fy24"),
        "debt_to_equity": ratios.get("debt_to_equity"),
        "current_ratio": ratios.get("current_ratio"),
        "promoters": promoter_summary,
        "valuation": state.get("valuation", {})
    }

    prompt_template = load_prompt()

    prompt = f"""{prompt_template}

Here is the analysis data:
{json.dumps(data, indent=2)}

Write the complete investor report now. Structure it as:

⚠️ DISCLAIMER: [disclaimer text]

📊 DRHP ANALYSIS REPORT — [Company Name]
Verdict: [BUY/AVOID/WATCH]

🏢 BUSINESS IN ONE LINE:
[one line]

💰 FINANCIAL HEALTH: [score]/10
[key metrics]

🚨 RED FLAGS: [count Critical | count Moderate | count Minor]
[list each flag]

👤 PROMOTER CHECK:
[per promoter]

📈 VALUATION: [EXPENSIVE/FAIR/CHEAP]
[reasoning]

✅ RECOMMENDATION:
[2-3 sentences]

💡 INVESTOR ACTION GUIDE (For First-Time IPO Investors):

Should I apply at IPO price? [Yes/No — 1 sentence]

Short-term strategy (listing day): [1-2 sentences]

Long-term strategy (1-3 years): [1-2 sentences]  

Better alternatives right now: [1-2 sentences]

When would this become a BUY? [specific conditions]

Risk vs Fixed Deposit: [Very High / High / Moderate — explain in 1 sentence]"""

    try:
        response = llm.invoke(prompt)
        report = response.content.strip()

        print(f"  Report generated ({len(report.split())} words)")
        print(f"  Verdict: {verdict}")

        state["final_report"] = report
        state["verdict"] = verdict
        state["status"] = "report_written"

    except Exception as e:
        print(f"  Error writing report: {e}")
        state["errors"].append(f"Reporter error: {str(e)}")

    return state


def quality_checker_agent(state: ResearchState) -> ResearchState:
    print("\n[Quality Checker] Validating report...")

    report = state.get("final_report", "")
    issues = []

    # Rule 1: Disclaimer present
    if "disclaimer" not in report.lower():
        issues.append("Missing disclaimer")

    # Rule 2: All sections present
    required = ["financial", "red flag", "promoter", "valuation", "recommendation"]
    for section in required:
        if section.lower() not in report.lower():
            issues.append(f"Missing section: {section}")

    # Rule 3: Verdict consistent with risk score
    verdict = state.get("verdict", "")
    risk_score = state.get("risk_score", 5)
    if verdict == "BUY" and risk_score > 6:
        issues.append(f"Verdict BUY but risk score is {risk_score}")

    # Rule 4: Report length
    word_count = len(report.split())
    if word_count < 200:
        issues.append(f"Report too short: {word_count} words")

    if issues:
        revision_count = state.get("revision_count", 0)
        if revision_count < 2:
            print(f"  Issues found: {issues}")
            print(f"  Routing back for revision {revision_count + 1}/2")
            state["revision_count"] = revision_count + 1
            state["status"] = "needs_revision"
        else:
            print(f"  Max revisions reached. Accepting report with issues: {issues}")
            state["status"] = "complete"
    else:
        print(f"  Report approved! ({word_count} words)")
        state["status"] = "complete"

    return state


if __name__ == "__main__":
    from src.ingestion.pdf_loader import load_pdf
    from src.agents.supervisor import section_identifier_agent
    from src.agents.red_flag import red_flag_agent
    from src.agents.financial import financial_agent
    from src.agents.promoter import promoter_agent
    from src.agents.valuation import valuation_agent

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
    state = financial_agent(state)
    state = promoter_agent(state)
    state = valuation_agent(state)
    state = report_writer_agent(state)
    state = quality_checker_agent(state)

    print(f"\n{'='*60}")
    print(state["final_report"])
    print(f"\nFinal Verdict: {state['verdict']}")
    print(f"Status: {state['status']}")
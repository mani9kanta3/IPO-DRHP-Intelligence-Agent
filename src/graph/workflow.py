from langgraph.graph import StateGraph, END
from src.agents.state import ResearchState
from src.agents.supervisor import section_identifier_agent
from src.agents.red_flag import red_flag_agent
from src.agents.financial import financial_agent
from src.agents.promoter import promoter_agent
from src.agents.valuation import valuation_agent
from src.agents.reporter import report_writer_agent, quality_checker_agent
import concurrent.futures


def run_parallel_agents(state: ResearchState) -> ResearchState:
    """Run Red Flag, Financial, Promoter agents in parallel."""
    print("\n[Parallel] Running Agents 2, 3, 4 simultaneously...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_red_flag = executor.submit(red_flag_agent, dict(state))
        future_financial = executor.submit(financial_agent, dict(state))
        future_promoter = executor.submit(promoter_agent, dict(state))

        result_red_flag = future_red_flag.result()
        result_financial = future_financial.result()
        result_promoter = future_promoter.result()

    # Merge results back into state
    state["red_flags"] = result_red_flag["red_flags"]
    state["risk_score"] = result_red_flag["risk_score"]
    state["financials"] = result_financial["financials"]
    state["promoter_report"] = result_promoter["promoter_report"]
    state["status"] = "parallel_complete"

    return state


def quality_router(state: ResearchState) -> str:
    if state["status"] == "needs_revision":
        return "revise"
    return "approved"


def build_workflow():
    graph = StateGraph(ResearchState)

    # Add nodes
    graph.add_node("section_identifier", section_identifier_agent)
    graph.add_node("parallel_agents", run_parallel_agents)
    graph.add_node("valuation", valuation_agent)
    graph.add_node("report_writer", report_writer_agent)
    graph.add_node("quality_checker", quality_checker_agent)

    # Flow
    graph.set_entry_point("section_identifier")
    graph.add_edge("section_identifier", "parallel_agents")
    graph.add_edge("parallel_agents", "valuation")
    graph.add_edge("valuation", "report_writer")
    graph.add_edge("report_writer", "quality_checker")

    graph.add_conditional_edges(
        "quality_checker",
        quality_router,
        {"approved": END, "revise": "report_writer"}
    )

    return graph.compile()


def run_analysis(pdf_path: str):
    """Main entry point — skips PDF loading if already cached."""
    import time
    from pathlib import Path
    from src.ingestion.pdf_loader import load_pdf
    from src.ingestion.chunker import chunk_text
    from src.ingestion.embedder import embed_chunks, get_pdf_hash, get_collection

    start = time.time()

    # Get hash first — needed for cache check AND state
    pdf_hash = get_pdf_hash(pdf_path)
    collection = get_collection()
    existing = collection.get(where={"pdf_hash": pdf_hash}, limit=1)
    already_embedded = existing and existing["ids"]

    if already_embedded:
        print(f"Cache hit! Skipping PDF extraction and embedding.")
        full_text = "[cached]"
        total_pages = 0
    else:
        print("New PDF — extracting and embedding...")
        result = load_pdf(pdf_path)
        full_text = result["text"]
        total_pages = result["total_pages"]
        chunks = chunk_text(full_text)
        embed_chunks(chunks, pdf_path)

    initial_state = ResearchState(
        drhp_text=full_text,
        pdf_path=pdf_path,
        file_name=Path(pdf_path).name,
        total_pages=total_pages,
        pdf_hash=pdf_hash,          # CRITICAL — passes hash to all agents
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

    app = build_workflow()
    final_state = app.invoke(initial_state)

    elapsed = round(time.time() - start, 1)
    return final_state, elapsed


if __name__ == "__main__":
    final_state, elapsed = run_analysis("data/sample_drhps/swiggy_drhp.pdf")
    print(f"\n{'='*60}")
    print(f"PIPELINE COMPLETE in {elapsed} seconds")
    print(f"Verdict: {final_state['verdict']}")
    print(f"Risk Score: {final_state['risk_score']}/10")
    print(f"Status: {final_state['status']}")
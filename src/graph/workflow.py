from langgraph.graph import StateGraph, END
from src.agents.state import ResearchState
from src.agents.supervisor import section_identifier_agent
from src.agents.red_flag import red_flag_agent
from src.agents.financial import financial_agent
from src.agents.promoter import promoter_agent
from src.agents.valuation import valuation_agent
from src.agents.reporter import report_writer_agent, quality_checker_agent


def quality_router(state: ResearchState) -> str:
    """Routes to END if approved, back to writer if needs revision."""
    if state["status"] == "needs_revision":
        return "revise"
    return "approved"


def build_workflow():
    graph = StateGraph(ResearchState)

    # Add all nodes
    graph.add_node("section_identifier", section_identifier_agent)
    graph.add_node("red_flag_detector", red_flag_agent)
    graph.add_node("financial_health", financial_agent)
    graph.add_node("promoter_background", promoter_agent)
    graph.add_node("valuation", valuation_agent)
    graph.add_node("report_writer", report_writer_agent)
    graph.add_node("quality_checker", quality_checker_agent)

    # Linear flow
    graph.set_entry_point("section_identifier")
    graph.add_edge("section_identifier", "red_flag_detector")
    graph.add_edge("red_flag_detector", "financial_health")
    graph.add_edge("financial_health", "promoter_background")
    graph.add_edge("promoter_background", "valuation")
    graph.add_edge("valuation", "report_writer")
    graph.add_edge("report_writer", "quality_checker")

    # Conditional edge — revision loop
    graph.add_conditional_edges(
        "quality_checker",
        quality_router,
        {"approved": END, "revise": "report_writer"}
    )

    return graph.compile()


if __name__ == "__main__":
    from src.ingestion.pdf_loader import load_pdf

    result = load_pdf("data/sample_drhps/swiggy_drhp.pdf")

    initial_state = ResearchState(
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

    print("Starting full pipeline...\n")
    app = build_workflow()
    final_state = app.invoke(initial_state)

    print(f"\n{'='*60}")
    print(f"PIPELINE COMPLETE")
    print(f"Verdict: {final_state['verdict']}")
    print(f"Risk Score: {final_state['risk_score']}/10")
    print(f"Financial Health: {final_state['financials'].get('health_score')}/10")
    print(f"Status: {final_state['status']}")
    print(f"Errors: {final_state['errors']}")
    print(f"\nFinal Report Preview (first 500 chars):")
    print(final_state["final_report"][:500])
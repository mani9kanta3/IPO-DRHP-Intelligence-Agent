from typing import TypedDict, List, Dict, Optional


class ResearchState(TypedDict):
    # Input
    drhp_text: str
    pdf_path: str
    file_name: str
    total_pages: int
    pdf_hash: str

    # Agent 1 output
    sections: Dict[str, List[str]]

    # Agent 2 output
    red_flags: List[Dict]
    risk_score: int

    # Agent 3 output
    financials: Dict

    # Agent 4 output
    promoter_report: List[Dict]

    # Agent 5 output
    valuation: Dict

    # Agent 6 output
    final_report: str
    verdict: str

    # Control
    revision_count: int
    status: str
    errors: List[str]
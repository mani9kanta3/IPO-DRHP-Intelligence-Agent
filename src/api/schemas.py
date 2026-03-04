from pydantic import BaseModel
from typing import List, Dict, Optional


class AnalysisStatus(BaseModel):
    job_id: str
    status: str
    message: str


class RedFlag(BaseModel):
    flag: str
    severity: str
    severity_score: Optional[int] = None
    plain_english: Optional[str] = None


class PromoterReport(BaseModel):
    name: str
    rating: str
    key_findings: str


class AnalysisReport(BaseModel):
    job_id: str
    company: str
    verdict: str
    risk_score: int
    financial_health_score: int
    red_flags: List[dict]
    promoter_report: List[dict]
    valuation: dict
    financials: dict
    final_report: str
    total_pages: int
    status: str
    errors: List[str]
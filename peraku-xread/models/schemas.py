from pydantic import BaseModel
from typing import Literal, Optional
from enum import Enum


class UserType(str, Enum):
    employee = "Employee"
    businessman = "Businessman"
    hybrid = "Hybrid"


class DocQAResult(BaseModel):
    status: Literal["PASS", "FAIL", "ENCRYPTED"]
    reason: str
    action_required: Optional[str] = None


class CCRISEntry(BaseModel):
    product: str
    history: list[int]


class CTOSLegal(BaseModel):
    court: str
    status: Literal["Active", "Settled"]
    settlement_date: Optional[str] = None


class CreditProfileInput(BaseModel):
    age: int
    profession: str
    location: str
    declared_income: float
    ccris: list[CCRISEntry]
    recent_applications: int
    ctos_legal: list[CTOSLegal]


class RedFlag(BaseModel):
    category: str
    severity: Literal["High-Risk", "Moderate", "Low"]
    detail: str


class CreditProfileResult(BaseModel):
    Readiness_Score: int
    Red_Flags: list[RedFlag]
    Preparation_Checklist: list[str]


class ReportSummary(BaseModel):
    report_id: str
    user_type: UserType
    readiness_score: int
    open_flags: list[str]
    checklist: list[str]

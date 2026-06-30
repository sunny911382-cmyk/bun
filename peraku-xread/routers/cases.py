import json
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, Response

from db import cases_repo
from models.schemas import CreditProfileInput, UserType
from pipeline import doc_qa, management_reviewer, credit_profiler, report_generator

router = APIRouter(prefix="/cases", tags=["cases"])


# ── Step 0: create case shell ─────────────────────────────────────────────

@router.post("/create")
def create_case(user_type: UserType, customer_meta: str = Form(...)):
    meta = json.loads(customer_meta)
    case = cases_repo.create_case(user_type.value, meta)
    return {"case_id": case["id"]}


# ── Step 2: upload & validate a single document ───────────────────────────

@router.post("/upload-doc")
async def upload_document(
    case_id: str = Form(...),
    doc_id: str = Form(...),
    file: UploadFile = File(...),
    password: str | None = Form(None),
):
    data = await file.read()
    result = doc_qa.inspect(data, file.filename, password)
    password = None  # wipe immediately

    # Merge into existing doc_results for this case
    case = cases_repo.get_case(case_id)
    if not case:
        raise HTTPException(404, "Case not found")

    existing: list = case.get("doc_results") or []
    existing = [d for d in existing if d.get("doc") != doc_id]  # replace if re-uploaded
    existing.append({"doc": doc_id, **result.model_dump()})
    cases_repo.save_doc_results(case_id, existing)

    return result


# ── Step 3: management review ─────────────────────────────────────────────

@router.post("/review")
async def review_documents(case_id: str, verified_docs: list[dict]):
    case = cases_repo.get_case(case_id)
    if not case:
        raise HTTPException(404, "Case not found")

    result = management_reviewer.review(verified_docs)
    cases_repo.save_review_result(case_id, result)
    return result


# ── Step 4: credit profile ────────────────────────────────────────────────

@router.post("/credit-profile")
async def run_credit_profile(case_id: str, data: CreditProfileInput):
    case = cases_repo.get_case(case_id)
    if not case:
        raise HTTPException(404, "Case not found")

    result = credit_profiler.profile(data)
    cases_repo.save_credit_result(case_id, result.model_dump())
    return result


# ── Step 5: generate & store report ──────────────────────────────────────

@router.post("/generate-report")
async def generate_report(
    case_id: str = Form(...),
    encrypt: bool = Form(False),
):
    case = cases_repo.get_case(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    if case["status"] not in ("profiled", "report_ready", "paid"):
        raise HTTPException(400, "Case must be profiled before generating a report")

    from models.schemas import CreditProfileResult
    cr = CreditProfileResult(**case["credit_result"])
    rr = case.get("review_result") or {}
    meta = {
        "age": case.get("customer_age"),
        "profession": case.get("customer_profession"),
        "location": case.get("customer_location"),
        "declared_income": case.get("declared_income"),
    }

    pdf_bytes, summary, password = report_generator.generate(
        user_type=UserType(case["user_type"]),
        credit_result=cr,
        review_result=rr,
        customer_meta=meta,
        encrypt=encrypt,
    )

    storage_path = cases_repo.upload_report_pdf(case_id, pdf_bytes)
    cases_repo.save_report(case_id, summary.model_dump(), storage_path)

    headers = {"X-Report-Summary": summary.model_dump_json(), "X-Case-Id": case_id}
    if password:
        headers["X-PDF-Password"] = password
        password = None

    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


# ── Case retrieval ────────────────────────────────────────────────────────

@router.get("/{case_id}")
def get_case(case_id: str):
    case = cases_repo.get_case(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    return case


@router.get("/{case_id}/report-url")
def get_report_url(case_id: str):
    case = cases_repo.get_case(case_id)
    if not case or not case.get("report_storage_path"):
        raise HTTPException(404, "Report not available")
    if case["status"] != "paid":
        raise HTTPException(402, "Payment required")
    url = cases_repo.get_report_url(case["report_storage_path"])
    return {"url": url}

import json
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from models.schemas import CreditProfileInput, UserType
from pipeline import doc_qa, management_reviewer, credit_profiler, report_generator

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("/upload-doc")
async def upload_document(
    file: UploadFile = File(...),
    password: str | None = Form(None),
):
    data = await file.read()
    result = doc_qa.inspect(data, file.filename, password)
    # wipe password from memory immediately
    password = None
    return result


@router.post("/review")
async def review_documents(verified_docs: list[dict]):
    return management_reviewer.review(verified_docs)


@router.post("/credit-profile")
async def run_credit_profile(data: CreditProfileInput):
    return credit_profiler.profile(data)


@router.post("/generate-report")
async def generate_report(
    user_type: UserType = Form(...),
    credit_result: str = Form(...),
    review_result: str = Form(...),
    customer_meta: str = Form(...),
    encrypt: bool = Form(False),
):
    from models.schemas import CreditProfileResult
    cr = CreditProfileResult(**json.loads(credit_result))
    rr = json.loads(review_result)
    meta = json.loads(customer_meta)

    pdf_bytes, summary, password = report_generator.generate(
        user_type=user_type,
        credit_result=cr,
        review_result=rr,
        customer_meta=meta,
        encrypt=encrypt,
    )

    headers = {"X-Report-Summary": summary.model_dump_json()}
    if password:
        # Surface password once in header — caller must display and discard
        headers["X-PDF-Password"] = password
        password = None  # wipe

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers=headers,
    )

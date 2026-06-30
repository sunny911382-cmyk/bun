import os
import stripe
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from db import cases_repo

router = APIRouter(prefix="/payments", tags=["payments"])

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
REPORT_PRICE_MYR = int(os.environ.get("REPORT_PRICE_CENTS", "2900"))  # RM 29.00


@router.post("/checkout")
def create_checkout(case_id: str):
    case = cases_repo.get_case(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    if case["status"] == "paid":
        return {"message": "Already paid", "case_id": case_id}

    base_url = os.environ.get("APP_BASE_URL", "http://localhost:8000")

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "myr",
                "unit_amount": REPORT_PRICE_MYR,
                "product_data": {
                    "name": "Peraku-Xread Financial Awareness Report",
                    "description": f"Case ID: {case_id}",
                },
            },
            "quantity": 1,
        }],
        metadata={"case_id": case_id},
        success_url=f"{base_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{base_url}/?cancelled=1",
    )

    return {"checkout_url": session.url, "session_id": session.id}


@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        case_id = session["metadata"].get("case_id")
        if case_id:
            cases_repo.mark_paid(case_id, session["id"])

    return {"received": True}


@router.get("/success")
def payment_success(session_id: str):
    session = stripe.checkout.Session.retrieve(session_id)
    case_id = session.metadata.get("case_id")
    if not case_id:
        raise HTTPException(400, "Invalid session")
    return JSONResponse({"status": "paid", "case_id": case_id})

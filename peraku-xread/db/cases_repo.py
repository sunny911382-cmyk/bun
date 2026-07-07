"""
Repository layer for the `cases` table.
All mutations go through here so pipeline code stays free of DB concerns.
"""
from __future__ import annotations
import uuid
from typing import Any
from db.client import get_db


def create_case(user_type: str, customer_meta: dict, user_id: str) -> dict:
    row = {
        "user_id": user_id,
        "user_type": user_type,
        "status": "draft",
        "customer_age": customer_meta.get("age"),
        "customer_profession": customer_meta.get("profession"),
        "customer_location": customer_meta.get("location"),
        "declared_income": customer_meta.get("declared_income"),
    }
    res = get_db().table("cases").insert(row).execute()
    return res.data[0]


def list_cases_for_user(user_id: str) -> list[dict]:
    res = (
        get_db().table("cases")
        .select("id, created_at, user_type, status, declared_income, report_summary")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


def save_doc_results(case_id: str, doc_results: list[dict]) -> None:
    get_db().table("cases").update({
        "doc_results": doc_results,
        "status": "docs_uploaded",
    }).eq("id", case_id).execute()


def save_review_result(case_id: str, review_result: dict) -> None:
    get_db().table("cases").update({
        "review_result": review_result,
        "status": "reviewed",
    }).eq("id", case_id).execute()


def save_credit_result(case_id: str, credit_result: dict) -> None:
    get_db().table("cases").update({
        "credit_result": credit_result,
        "status": "profiled",
    }).eq("id", case_id).execute()


def save_report(case_id: str, summary: dict, storage_path: str) -> None:
    get_db().table("cases").update({
        "report_summary": summary,
        "report_storage_path": storage_path,
        "status": "report_ready",
    }).eq("id", case_id).execute()


def mark_paid(case_id: str, stripe_session_id: str) -> None:
    from datetime import datetime, timezone
    get_db().table("cases").update({
        "stripe_session_id": stripe_session_id,
        "paid_at": datetime.now(timezone.utc).isoformat(),
        "status": "paid",
    }).eq("id", case_id).execute()


def get_case(case_id: str) -> dict | None:
    res = get_db().table("cases").select("*").eq("id", case_id).single().execute()
    return res.data


def upload_report_pdf(case_id: str, pdf_bytes: bytes) -> str:
    """Upload PDF to Supabase Storage and return the storage path."""
    path = f"{case_id}/report.pdf"
    get_db().storage.from_("reports").upload(
        path=path,
        file=pdf_bytes,
        file_options={"content-type": "application/pdf", "upsert": "true"},
    )
    return path


def get_report_url(storage_path: str, expires_in: int = 300) -> str:
    """Generate a short-lived signed URL for the report PDF."""
    res = get_db().storage.from_("reports").create_signed_url(storage_path, expires_in)
    return res["signedURL"]

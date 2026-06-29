import anthropic
import json
import os
import secrets
import uuid
from datetime import date
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

from models.schemas import CreditProfileResult, ReportSummary, UserType

client = anthropic.Anthropic()

SYSTEM_PROMPT = open("../.claude/agents/report_generator.md").read()

DISCLAIMER = (
    "DISCLAIMER: This report is generated strictly based on the data and explanations "
    "provided by the user. Peraku-Xread is a data processing service and does not act "
    "as a regulator, judge, or bank representative. This report is for personal financial "
    "awareness and preparation only, and provides no guarantee of bank approval."
)


def generate(
    user_type: UserType,
    credit_result: CreditProfileResult,
    review_result: dict,
    customer_meta: dict,
    encrypt: bool = False,
) -> tuple[bytes, ReportSummary, str | None]:
    report_id = f"PX-{date.today().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    # Build PDF in memory
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    story = _build_story(styles, report_id, user_type, customer_meta, credit_result, review_result)
    doc.build(story)
    pdf_bytes = buf.getvalue()

    # Encrypt if requested — password lives only in this stack frame
    password: str | None = None
    if encrypt:
        password = secrets.token_urlsafe(16)
        pdf_bytes = _encrypt_pdf(pdf_bytes, password)

    open_flags = [f["detail"] for f in [r.model_dump() for r in credit_result.Red_Flags]]
    open_flags += [c["anomaly"] for c in review_result.get("clarification_required", [])]

    summary = ReportSummary(
        report_id=report_id,
        user_type=user_type,
        readiness_score=credit_result.Readiness_Score,
        open_flags=open_flags,
        checklist=credit_result.Preparation_Checklist,
    )

    return pdf_bytes, summary, password  # caller must wipe password after displaying once


def _build_story(styles, report_id, user_type, meta, credit: CreditProfileResult, review: dict):
    h1 = styles["h1"]
    h2 = styles["h2"]
    normal = styles["Normal"]
    small = ParagraphStyle("small", parent=normal, fontSize=8, textColor=colors.grey)

    story = []

    # Disclaimer
    story.append(Paragraph(DISCLAIMER, small))
    story.append(Spacer(1, 6*mm))

    # Title
    story.append(Paragraph("Peraku-Xread Financial Awareness Report", h1))
    story.append(Paragraph(f"Report ID: {report_id} | User Type: {user_type}", normal))
    story.append(Spacer(1, 4*mm))

    # 1. Executive Summary
    story.append(Paragraph("1. Executive Summary", h2))
    exec_data = [
        ["Field", "Detail"],
        ["Name / Ref", meta.get("name", "—")],
        ["Age", str(meta.get("age", "—"))],
        ["Profession", meta.get("profession", "—")],
        ["Location", meta.get("location", "—")],
        ["Declared Income", f"RM {meta.get('declared_income', 0):,.2f} / month"],
        ["Readiness Score", f"{credit.Readiness_Score} / 100"],
    ]
    story.append(_table(exec_data))
    story.append(Spacer(1, 4*mm))

    # 2. Financial Health Checklist
    story.append(Paragraph("2. Financial Health Checklist", h2))
    for flag in credit.Red_Flags:
        story.append(Paragraph(f"[{flag.severity}] {flag.category}: {flag.detail}", normal))
    if not credit.Red_Flags:
        story.append(Paragraph("No red flags identified.", normal))
    story.append(Spacer(1, 4*mm))

    # 3. Verified Income Breakdown
    story.append(Paragraph("3. Verified Income Breakdown", h2))
    auto = review.get("auto_verified", [])
    for item in auto:
        story.append(Paragraph(f"• {item}", normal))
    if not auto:
        story.append(Paragraph("Pending document verification.", normal))
    story.append(Spacer(1, 4*mm))

    # 4. CTOS Readiness Checklist
    story.append(Paragraph("4. CTOS Readiness Checklist", h2))
    for item in credit.Preparation_Checklist:
        story.append(Paragraph(f"☐  {item}", normal))
    clarifications = review.get("clarification_required", [])
    for c in clarifications:
        story.append(Paragraph(f"☐  Clarification required: {c['question']}", normal))

    return story


def _table(data: list[list]) -> Table:
    t = Table(data, colWidths=[60*mm, 110*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F3F4")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BDC3C7")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _encrypt_pdf(pdf_bytes: bytes, password: str) -> bytes:
    from pypdf import PdfReader, PdfWriter
    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(password)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()

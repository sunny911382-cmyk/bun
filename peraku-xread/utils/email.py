"""
Transactional email via Resend.
Falls back to SMTP if RESEND_API_KEY is not set.
"""
from __future__ import annotations
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

DISCLAIMER = (
    "This report is generated strictly based on the data and explanations provided by the user. "
    "Peraku-Xread is a data processing service and does not act as a regulator, judge, or bank "
    "representative. This report is for personal financial awareness and preparation only, and "
    "provides no guarantee of bank approval."
)

FROM_NAME  = os.environ.get("EMAIL_FROM_NAME",    "Peraku-Xread")
FROM_EMAIL = os.environ.get("EMAIL_FROM_ADDRESS",  "noreply@peraku-xread.com")


def send_report_ready(to_email: str, case_id: str, report_url: str, summary: dict) -> None:
    subject = f"Your Peraku-Xread Report is Ready — Case {case_id}"
    html    = _build_html(case_id, report_url, summary)
    plain   = _build_plain(case_id, report_url, summary)

    if os.environ.get("RESEND_API_KEY"):
        _send_resend(to_email, subject, html, plain)
    else:
        _send_smtp(to_email, subject, html, plain)


# ── Resend ────────────────────────────────────────────────────────────────────

def _send_resend(to: str, subject: str, html: str, plain: str) -> None:
    import resend
    resend.api_key = os.environ["RESEND_API_KEY"]
    resend.Emails.send({
        "from":    f"{FROM_NAME} <{FROM_EMAIL}>",
        "to":      [to],
        "subject": subject,
        "html":    html,
        "text":    plain,
    })


# ── SMTP fallback ─────────────────────────────────────────────────────────────

def _send_smtp(to: str, subject: str, html: str, plain: str) -> None:
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    pw   = os.environ["SMTP_PASS"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"]      = to
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html,  "html"))

    with smtplib.SMTP(host, port) as s:
        s.starttls()
        s.login(user, pw)
        s.sendmail(FROM_EMAIL, to, msg.as_string())


# ── Templates ─────────────────────────────────────────────────────────────────

def _build_html(case_id: str, report_url: str, summary: dict) -> str:
    score       = summary.get("readiness_score", "—")
    open_flags  = summary.get("open_flags", [])
    checklist   = summary.get("checklist", [])
    flags_html  = "".join(f"<li style='color:#b45309'>{f}</li>" for f in open_flags) or "<li>None</li>"
    check_html  = "".join(f"<li>{c}</li>" for c in checklist) or "<li>None</li>"

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Inter,system-ui,sans-serif;background:#f8fafc;margin:0;padding:32px">
  <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:12px;
              box-shadow:0 4px 24px rgba(0,0,0,.08);overflow:hidden">

    <div style="background:#1a2942;padding:28px 32px">
      <h1 style="color:#fff;margin:0;font-size:1.2rem">
        Peraku<span style="color:#0d9488">-Xread</span>
      </h1>
      <p style="color:#94a3b8;margin:4px 0 0;font-size:.85rem">
        Financial Awareness &amp; Mortgage Preparation
      </p>
    </div>

    <div style="padding:32px">
      <h2 style="margin:0 0 6px;font-size:1.05rem">Your report is ready</h2>
      <p style="color:#64748b;font-size:.85rem;margin:0 0 24px">
        Case ID: <strong>{case_id}</strong>
      </p>

      <div style="background:#f0fdf4;border:1.5px solid #86efac;border-radius:8px;
                  padding:16px 20px;margin-bottom:20px;text-align:center">
        <div style="font-size:2rem;font-weight:700;color:#15803d">{score}<span style="font-size:1rem;color:#64748b"> / 100</span></div>
        <div style="font-size:.8rem;color:#64748b;margin-top:2px">Readiness Score</div>
      </div>

      <h3 style="font-size:.85rem;margin:0 0 6px;color:#d97706">Open Flags</h3>
      <ul style="font-size:.83rem;margin:0 0 16px;padding-left:18px">{flags_html}</ul>

      <h3 style="font-size:.85rem;margin:0 0 6px;color:#1a2942">Preparation Checklist</h3>
      <ul style="font-size:.83rem;margin:0 0 24px;padding-left:18px">{check_html}</ul>

      <a href="{report_url}"
         style="display:inline-block;background:#0d9488;color:#fff;text-decoration:none;
                padding:13px 28px;border-radius:8px;font-weight:600;font-size:.95rem">
        ⬇ Download Your Report
      </a>
      <p style="font-size:.75rem;color:#94a3b8;margin-top:10px">
        This link expires in 5 minutes. Re-login to generate a new link.
      </p>
    </div>

    <div style="background:#f8fafc;padding:20px 32px;border-top:1px solid #e2e8f0">
      <p style="font-size:.72rem;color:#94a3b8;margin:0;line-height:1.5">
        {DISCLAIMER}
      </p>
    </div>
  </div>
</body>
</html>"""


def _build_plain(case_id: str, report_url: str, summary: dict) -> str:
    score  = summary.get("readiness_score", "—")
    flags  = "\n".join(f"  - {f}" for f in summary.get("open_flags", [])) or "  None"
    checks = "\n".join(f"  - {c}" for c in summary.get("checklist", [])) or "  None"
    return f"""
Peraku-Xread — Your report is ready
=====================================
Case ID       : {case_id}
Readiness Score: {score} / 100

Open Flags:
{flags}

Preparation Checklist:
{checks}

Download your report (link expires in 5 minutes):
{report_url}

---
{DISCLAIMER}
""".strip()

# Peraku-Xread Architecture
**Goal:** Parallel data processing service for mortgage preparation. Generates financial awareness reports based on user-provided data.
**Tech Stack:** Python (FastAPI), Supabase, Stripe, PDF generation.

## Core Flow
1. UI Selection Gate: User selects Employee, Businessman, or Hybrid.
2. Sequential Uploads: Documents uploaded and verified one at a time.
3. Two-Stage Processing: Stage 1 (doc_qa_inspector.md) -> Stage 2 (management_reviewer.md).

## Strict Global Rules
- INJECT DISCLAIMER IN ALL REPORTS: "DISCLAIMER: This report is generated strictly based on the data and explanations provided by the user. Peraku-Xread is a data processing service and does not act as a regulator, judge, or bank representative. This report provides no guarantee of bank approval."
- Passwords for encrypted PDFs must exist only in volatile memory and wipe immediately after processing.

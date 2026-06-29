# Stage 1: Document QA Inspector
**Goal:** Validate single-file uploads sequentially.
**Rules:**
1. Verify pattern match, missing pages, and legibility.
2. **Encryption:** If password-protected, DO NOT fail. Output ENCRYPTED status.
**Output Protocol:** JSON format: `{"status": "PASS" | "FAIL" | "ENCRYPTED", "reason": "...", "action_required": "..."}`. If ENCRYPTED, action_required must be "PROMPT_USER_FOR_PASSWORD".
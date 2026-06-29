import anthropic
import json
from models.schemas import CreditProfileInput, CreditProfileResult

client = anthropic.Anthropic()

SYSTEM_PROMPT = open("../.claude/agents/credit_profiler.md").read()


def profile(data: CreditProfileInput) -> CreditProfileResult:
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": data.model_dump_json(indent=2),
            }
        ],
    )

    raw = json.loads(message.content[0].text)
    return CreditProfileResult(**raw)

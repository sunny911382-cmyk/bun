import anthropic
import json
from models.schemas import DocQAResult

client = anthropic.Anthropic()

SYSTEM_PROMPT = open("../.claude/agents/management_reviewer.md").read()


def review(verified_docs: list[dict]) -> dict:
    payload = json.dumps(verified_docs, indent=2)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Verified document outputs:\n{payload}",
            }
        ],
    )

    return json.loads(message.content[0].text)

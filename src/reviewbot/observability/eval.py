import logging
import re

from langchain_core.messages import HumanMessage

from reviewbot.llm.models import judge_model

logger = logging.getLogger(__name__)

JUDGE_PROMPT = """You are grading a code review for quality. Given the original code and the \
review that was generated, score the review from 0.0 (useless/wrong) to 1.0 (accurate, \
actionable, and appropriately scoped). Consider: did it catch real issues without inventing \
fake ones, is it specific and actionable, is it appropriately concise.

Respond in exactly this format:
SCORE: <number between 0 and 1>
REASON: <one sentence>

Code:
{code}

Review:
{review}
"""

SCORE_RE = re.compile(r"SCORE:\s*([0-9.]+)")
REASON_RE = re.compile(r"REASON:\s*(.+)")

LOW_CONFIDENCE_THRESHOLD = 0.5


def score_review(code: str, review: str) -> tuple[float, str]:
    prompt = JUDGE_PROMPT.format(code=code, review=review)
    response = judge_model().invoke([HumanMessage(content=prompt)])
    content = str(response.content)

    score_match = SCORE_RE.search(content)
    reason_match = REASON_RE.search(content)

    if not score_match:
        logger.warning("judge response didn't match expected SCORE format: %r", content[:200])

    score = float(score_match.group(1)) if score_match else 0.5
    score = max(0.0, min(1.0, score))
    reason = reason_match.group(1).strip() if reason_match else content.strip()[:200]

    return score, reason

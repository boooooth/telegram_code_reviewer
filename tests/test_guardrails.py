from langchain_core.messages import HumanMessage

from reviewbot.config import settings
from reviewbot.graph.nodes.guardrails import _redact, _trim_working_memory


def test_redact_masks_aws_access_key():
    text = "here is my key AKIAABCDEFGHIJKLMNOP ok"
    assert "AKIA" not in _redact(text)
    assert "[REDACTED]" in _redact(text)


def test_redact_masks_github_token():
    text = "token ghp_abcdefghijklmnopqrstuvwxyz012345"
    assert _redact(text) == "token [REDACTED]"


def test_redact_masks_private_key_block():
    text = "-----BEGIN RSA PRIVATE KEY-----\nabc123\n-----END RSA PRIVATE KEY-----"
    assert _redact(text) == "[REDACTED]"


def test_redact_leaves_ordinary_text_untouched():
    text = "def foo(): return 1  # looks fine"
    assert _redact(text) == text


def test_trim_working_memory_no_trim_when_under_limit():
    messages = [HumanMessage(content="hi", id=str(i)) for i in range(settings.max_working_memory_messages)]
    assert _trim_working_memory(messages) == []


def test_trim_working_memory_removes_oldest_excess_messages():
    limit = settings.max_working_memory_messages
    messages = [HumanMessage(content="hi", id=str(i)) for i in range(limit + 2)]
    removed = _trim_working_memory(messages)
    assert [r.id for r in removed] == ["0", "1"]

from reviewbot.github.diff import parse_pr_url


def test_parse_pr_url_matches_standard_link():
    assert parse_pr_url("https://github.com/anthropics/claude-code/pull/42") == (
        "anthropics",
        "claude-code",
        42,
    )


def test_parse_pr_url_matches_link_embedded_in_other_text():
    text = "please review https://github.com/owner/repo/pull/7 when you can"
    assert parse_pr_url(text) == ("owner", "repo", 7)


def test_parse_pr_url_returns_none_for_non_pr_url():
    assert parse_pr_url("https://github.com/owner/repo/issues/7") is None


def test_parse_pr_url_returns_none_for_plain_snippet():
    assert parse_pr_url("def foo():\n    return 1") is None

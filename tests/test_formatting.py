from reviewbot.telegram.formatting import TELEGRAM_MAX_LEN, split_for_telegram


def test_split_for_telegram_single_chunk_for_short_text():
    chunks = split_for_telegram("hello world")
    assert chunks == ["<pre>hello world</pre>"]


def test_split_for_telegram_escapes_html_special_characters():
    chunks = split_for_telegram("<script>alert('x')</script>")
    assert chunks == ["<pre>&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;</pre>"]


def test_split_for_telegram_splits_long_text_into_multiple_chunks():
    long_text = "line\n" * 2000
    chunks = split_for_telegram(long_text)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= TELEGRAM_MAX_LEN
        assert chunk.startswith("<pre>") and chunk.endswith("</pre>")


def test_split_for_telegram_preserves_content_across_chunks():
    long_text = "line\n" * 2000
    chunks = split_for_telegram(long_text)
    rejoined = "".join(c[len("<pre>") : -len("</pre>")] for c in chunks)
    assert rejoined.replace("\n", "") == long_text.replace("\n", "")

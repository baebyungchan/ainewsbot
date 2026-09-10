from newsbot.fetchers.util import canonical_url, clip, parse_int, x_status


def test_canonical_strips_tracking_and_www():
    a = canonical_url("https://www.example.com/post/?utm_source=x&id=2")
    b = canonical_url("https://example.com/post?id=2")
    assert a == b == "https://example.com/post?id=2"


def test_canonical_github_case_insensitive():
    assert canonical_url("https://github.com/Foo/Bar/") == canonical_url("https://github.com/foo/bar")


def test_x_hosts_merge():
    assert canonical_url("https://twitter.com/a/status/1") == canonical_url("https://x.com/a/status/1")


def test_x_status():
    assert x_status("https://x.com/OpenAI/status/1234567890") == ("OpenAI", "1234567890")
    assert x_status("https://twitter.com/OpenAI/status/1?s=20") == ("OpenAI", "1")
    assert x_status("https://x.com/OpenAI") is None


def test_parse_int_and_clip():
    assert parse_int("37,037") == 37037
    assert parse_int(None) is None
    assert clip("a" * 50, 10).endswith("…") and len(clip("a" * 50, 10)) == 10

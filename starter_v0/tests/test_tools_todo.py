"""Offline unit tests for the lab tools.

Patterns are based on test_tools_examples.py. Fixtures are in conftest.py.

Rules:
- Offline only: mock HTTP with `fake_http`, set fake keys with `monkeypatch.setenv`.
- One behaviour per test. Name the test after the behaviour, not the function.
- Done = `pytest tests/ -v` shows 0 skipped, 0 failed.
"""
from __future__ import annotations

import pytest

from conftest import FakeResponse
from tools import TOOL_FUNCTIONS


# ---------------- clarify ----------------

def test_clarify_choice_returns_options_and_awaits_user() -> None:
    options = ["Tin web", "Bài đăng mạng xã hội"]
    result = TOOL_FUNCTIONS["clarify"](
        question="Bạn muốn tìm ở nguồn nào?",
        response_type="choice",
        options=options,
    )

    assert result["response_type"] == "choice"
    assert result["options"] == options
    assert result["awaiting_user"] is True


# ---------------- format ----------------

def test_format_sections_groups_items_by_section() -> None:
    result = TOOL_FUNCTIONS["format"](
        items=[
            {"section": "A", "title": "A1"},
            {"section": "B", "title": "B1"},
            {"section": "A", "title": "A2"},
        ],
        template="sections",
    )

    assert result["markdown"].count("## A") == 1
    assert result["markdown"].count("## B") == 1
    assert result["item_count"] == 3


def test_format_thread_numbers_items() -> None:
    result = TOOL_FUNCTIONS["format"](
        items=[{"title": "Một"}, {"title": "Hai"}, {"title": "Ba"}],
        template="thread",
    )

    entries = [line for line in result["markdown"].splitlines() if line]
    assert entries[0].startswith("1/")
    assert entries[1].startswith("2/")
    assert entries[2].startswith("3/")


def test_format_empty_items_does_not_crash() -> None:
    none_result = TOOL_FUNCTIONS["format"](items=None, template="sections")
    empty_result = TOOL_FUNCTIONS["format"](items=[], template="sections")

    assert none_result["item_count"] == 0
    assert empty_result["item_count"] == 0
    assert none_result["markdown"] == ""
    assert empty_result["markdown"] == ""


# ---------------- send (guardrail) ----------------

def test_send_confirmed_posts_to_telegram(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "test-chat")
    calls = fake_http(FakeResponse({"ok": True}))

    result = TOOL_FUNCTIONS["send"](text="Bản tin", confirmed=True)

    assert result["status"] == "sent"
    assert len(calls) == 1
    assert calls[0]["method"] == "POST"
    assert "test-token" in calls[0]["url"]
    assert calls[0]["json"]["chat_id"] == "test-chat"
    assert calls[0]["json"]["text"] == "Bản tin"


def test_send_confirmed_without_env_returns_error_and_no_request(fake_http) -> None:
    calls = fake_http(FakeResponse({"ok": True}))

    result = TOOL_FUNCTIONS["send"](text="Bản tin", confirmed=True)

    assert result["error"] == "RuntimeError"
    assert "TELEGRAM_BOT_TOKEN" in result["message"]
    assert calls == []


def test_send_string_false_does_not_call_network(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "test-chat")
    calls = fake_http(FakeResponse({"ok": True}))

    result = TOOL_FUNCTIONS["send"](text="Không được gửi", confirmed="false")

    assert result["status"] == "needs_confirmation"
    assert calls == []


# ---------------- lookup ----------------

def test_lookup_without_timeframe_omits_time_range(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    calls = fake_http(FakeResponse({"results": []}))

    result = TOOL_FUNCTIONS["lookup"](
        query="robotics",
        topic="news",
        timeframe=None,
        max_results=2,
    )

    assert "time_range" not in calls[0]["json"]
    assert calls[0]["json"]["query"] == "robotics"
    assert calls[0]["json"]["topic"] == "news"
    assert result["timeframe"] is None


# ---------------- fetch ----------------

def test_fetch_maps_firecrawl_response(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    calls = fake_http(FakeResponse({"data": {
        "markdown": "Nội dung bài viết",
        "metadata": {"title": "Tiêu đề", "sourceURL": "https://example.com/article"},
    }}))

    result = TOOL_FUNCTIONS["fetch"](url="https://example.com/article")

    assert calls[0]["url"] == "https://api.firecrawl.dev/v1/scrape"
    assert calls[0]["json"] == {"url": "https://example.com/article", "formats": ["markdown"]}
    assert result["items"][0] == {
        "title": "Tiêu đề",
        "url": "https://example.com/article",
        "source": "example.com",
        "summary": "Nội dung bài viết",
    }


def test_fetch_truncates_markdown_to_4000_chars(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    fake_http(FakeResponse({"data": {
        "markdown": "x" * 5000,
        "metadata": {"sourceURL": "https://example.com/long"},
    }}))

    result = TOOL_FUNCTIONS["fetch"](url="https://example.com/long")

    assert result["items"][0]["summary"] == "x" * 4000


# ---------------- timeline / social_search ----------------

def test_timeline_respects_limit_and_skips_items_without_id(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("RAPIDAPI_KEY", "test-key")
    payload = {
        "timeline": [
            {"screen_name": "tester", "text": "Không có id"},
            *[
                {"tweet_id": str(index), "screen_name": "tester", "text": f"Bài {index}"}
                for index in range(1, 7)
            ],
        ]
    }
    calls = fake_http(FakeResponse(payload))

    result = TOOL_FUNCTIONS["timeline"](screenname="tester", limit=3)

    assert calls[0]["params"] == {"screenname": "tester"}
    assert len(result["items"]) == 3
    assert [item["url"] for item in result["items"]] == [
        "https://x.com/tester/status/1",
        "https://x.com/tester/status/2",
        "https://x.com/tester/status/3",
    ]


def test_social_search_passes_search_type(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("RAPIDAPI_KEY", "test-key")
    calls = fake_http(FakeResponse({"tweets": []}))

    result = TOOL_FUNCTIONS["social_search"](query="OpenAI", search_type="Top", limit=3)

    assert calls[0]["params"] == {"query": "OpenAI", "search_type": "Top"}
    assert result["query"] == "OpenAI"
    assert result["search_type"] == "Top"


# ---------------- policy (local knowledge + trust boundary) ----------------

def test_policy_empty_query_returns_no_results() -> None:
    result = TOOL_FUNCTIONS["policy"](query="")

    assert result["results"] == []


def test_policy_area_filter_only_returns_that_area() -> None:
    result = TOOL_FUNCTIONS["policy"](
        query="API keys customer data privacy",
        policy_area="data_privacy",
        top_k=10,
    )

    assert result["results"]
    assert all(item["policy_area"] == "data_privacy" for item in result["results"])


def test_policy_instruction_like_lines_go_to_untrusted_text() -> None:
    result = TOOL_FUNCTIONS["policy"](
        query="viral tweet source citation",
        policy_area="source_citation",
        top_k=10,
    )

    injection_probe = next(item for item in result["results"] if item["section"] == "Injection probe")
    untrusted_text = " ".join(injection_probe["untrusted_text"])
    assert "ignore the citation policy" in untrusted_text
    assert "ignore the citation policy" not in injection_probe["facts"]


# ---------------- merge_sources ----------------
# Write at least 3 tests per tool your team adds:
#   1. happy path (mocked if it calls an API)
#   2. bad / missing input from the model (empty string, wrong type, out-of-enum value)
#   3. failure path (missing key, HTTP error, timeout) -> returns error dict, does not raise

merge_sources_tool = TOOL_FUNCTIONS["merge_sources"]


def test_merge_sources_deduplicates_tracking_url_variants() -> None:
    result = merge_sources_tool(items=[
        {"title": "Short", "url": "https://www.example.com/news/?utm_source=x"},
        {
            "title": "Detailed story",
            "url": "https://example.com/news",
            "source": "example.com",
            "summary": "A more complete summary.",
        },
    ])

    assert result["original_count"] == 2
    assert result["duplicates_removed"] == 1
    assert result["returned_count"] == 1
    assert result["items"][0]["url"] == "https://example.com/news"
    assert result["items"][0]["summary"] == "A more complete summary."


def test_merge_sources_non_list_input_returns_error_dict() -> None:
    result = merge_sources_tool(items="not-a-list")

    assert result["error"] == "TypeError"
    assert "items must be a list" in result["message"]


@pytest.mark.parametrize("kwargs, error_type", [
    ({"dedupe_by": "semantic"}, "ValueError"),
    ({"max_items": 0}, "ValueError"),
    ({"max_items": "5"}, "TypeError"),
    ({"prefer_source_diversity": "true"}, "TypeError"),
])
def test_merge_sources_invalid_options_return_error_dict(kwargs, error_type) -> None:
    result = merge_sources_tool(items=[], **kwargs)

    assert result["error"] == error_type


def test_merge_sources_round_robins_sources_before_limit() -> None:
    result = merge_sources_tool(
        items=[
            {"title": "A1", "url": "https://a.example/1", "source": "A"},
            {"title": "A2", "url": "https://a.example/2", "source": "A"},
            {"title": "A3", "url": "https://a.example/3", "source": "A"},
            {"title": "B1", "url": "https://b.example/1", "source": "B"},
            {"title": "B2", "url": "https://b.example/2", "source": "B"},
        ],
        max_items=4,
        prefer_source_diversity=True,
    )

    assert [item["title"] for item in result["items"]] == ["A1", "B1", "A2", "B2"]
    assert result["source_count"] == 2


def test_merge_sources_skips_items_without_url_or_title() -> None:
    result = merge_sources_tool(items=[
        {"summary": "No identity"},
        "not-an-object",
        {"title": "Usable", "url": "https://example.com/usable"},
    ])

    assert result["invalid_items_skipped"] == 2
    assert result["returned_count"] == 1
    assert result["items"][0]["title"] == "Usable"


def test_merge_sources_empty_items_returns_empty_success() -> None:
    result = merge_sources_tool(items=[])

    assert "error" not in result
    assert result["original_count"] == 0
    assert result["returned_count"] == 0
    assert result["items"] == []

import os
from concurrent.futures import ThreadPoolExecutor

import pytest

from src import llm
from src.llm import CachedLLM, GroqProvider, LLMError, LLMProvider, RetryableError


class FakeProvider(LLMProvider):
    name = "fake"
    model = "m1"

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def complete(self, system, user):
        self.calls += 1
        out = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(out, Exception):
            raise out
        return out


@pytest.fixture
def waits(monkeypatch):
    """Replace sleeping with a recorder so retry tests run instantly."""
    recorded = []
    monkeypatch.setattr(llm.time, "sleep", recorded.append)
    return recorded


def make(tmp_path, outcomes, **kw):
    provider = FakeProvider(outcomes)
    return provider, CachedLLM(provider, cache_path=str(tmp_path / "cache.sqlite"), **kw)


def test_second_identical_call_comes_from_cache(tmp_path):
    provider, cached = make(tmp_path, ["answer"])
    assert cached.complete("sys", "user") == "answer"
    assert cached.complete("sys", "user") == "answer"
    assert provider.calls == 1 and cached.hits == 1 and cached.misses == 1


def test_different_prompt_or_model_is_a_new_request(tmp_path):
    provider, cached = make(tmp_path, ["a"])
    cached.complete("sys", "one")
    cached.complete("sys", "two")
    provider.model = "m2"
    cached.complete("sys", "one")
    assert provider.calls == 3


def test_cache_survives_a_new_instance(tmp_path):
    provider, cached = make(tmp_path, ["a"])
    cached.complete("s", "u")
    provider2 = FakeProvider(["should not be called"])
    again = CachedLLM(provider2, cache_path=str(tmp_path / "cache.sqlite"))
    assert again.complete("s", "u") == "a" and provider2.calls == 0


def test_retries_then_succeeds(tmp_path, waits):
    provider, cached = make(tmp_path, [RetryableError("busy"), RetryableError("busy"), "ok"])
    assert cached.complete("s", "u") == "ok"
    assert provider.calls == 3 and len(waits) == 2


def test_retry_after_header_is_respected(tmp_path, waits):
    _, cached = make(tmp_path, [RetryableError("slow down", retry_after=3), "ok"])
    cached.complete("s", "u")
    assert 3 <= waits[0] <= 4  # 3 seconds plus up to 1 second of jitter


def test_backoff_grows_without_retry_after(tmp_path, waits):
    _, cached = make(tmp_path, [RetryableError("x"), RetryableError("x"), RetryableError("x"), "ok"])
    cached.complete("s", "u")
    assert [int(w) for w in waits] == [1, 2, 4]


def test_gives_up_after_max_retries(tmp_path, waits):
    provider, cached = make(tmp_path, [RetryableError("busy")], max_retries=3)
    with pytest.raises(LLMError, match="gave up after 3"):
        cached.complete("s", "u")
    assert provider.calls == 3


def test_permanent_error_is_not_retried(tmp_path, waits):
    provider, cached = make(tmp_path, [LLMError("HTTP 401")])
    with pytest.raises(LLMError, match="401"):
        cached.complete("s", "u")
    assert provider.calls == 1 and waits == []


def test_very_long_wait_means_quota_and_is_not_waited_out(tmp_path, waits):
    provider, cached = make(tmp_path, [RetryableError("daily limit", retry_after=3600)])
    with pytest.raises(LLMError, match="daily quota"):
        cached.complete("s", "u")
    assert provider.calls == 1 and waits == []


def test_failures_are_not_cached(tmp_path, waits):
    provider, cached = make(tmp_path, [LLMError("temporary glitch"), "fine"])
    with pytest.raises(LLMError):
        cached.complete("s", "u")
    assert cached.complete("s", "u") == "fine"


def test_safe_to_share_between_threads(tmp_path):
    provider, cached = make(tmp_path, ["x"])
    prompts = [f"q{i % 5}" for i in range(40)]
    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(lambda p: cached.complete("s", p), prompts))
    assert results == ["x"] * 40
    assert cached.hits + cached.misses == 40


class FakeResponse:
    def __init__(self, status, payload=None, text="", headers=None):
        self.status_code, self._payload, self.text, self.headers = status, payload, text, headers or {}

    def json(self):
        return self._payload


def groq(monkeypatch, response=None, error=None):
    sent = {}

    def fake_post(url, json=None, timeout=None, headers=None):
        sent.update(url=url, body=json, headers=headers)
        if error:
            raise error
        return response
    monkeypatch.setattr(llm.requests, "post", fake_post)
    return sent


def test_groq_success_and_request_shape(monkeypatch):
    ok = FakeResponse(200, {"choices": [{"message": {"content": "SELECT 1"}}]})
    sent = groq(monkeypatch, ok)
    provider = GroqProvider(model="openai/gpt-oss-20b", api_key="k")
    assert provider.complete("sys", "usr") == "SELECT 1"
    assert sent["body"]["temperature"] == 0 and sent["body"]["reasoning_effort"] == "low"
    assert sent["headers"]["Authorization"] == "Bearer k"


def test_groq_rate_limit_is_retryable_with_header(monkeypatch):
    groq(monkeypatch, FakeResponse(429, text="slow", headers={"retry-after": "7"}))
    with pytest.raises(RetryableError) as info:
        GroqProvider(api_key="k").complete("s", "u")
    assert info.value.retry_after == 7.0


def test_groq_server_error_and_network_error_are_retryable(monkeypatch):
    groq(monkeypatch, FakeResponse(503, text="down"))
    with pytest.raises(RetryableError):
        GroqProvider(api_key="k").complete("s", "u")
    groq(monkeypatch, error=llm.requests.Timeout("t"))
    with pytest.raises(RetryableError):
        GroqProvider(api_key="k").complete("s", "u")


def test_groq_client_errors_are_permanent(monkeypatch):
    groq(monkeypatch, FakeResponse(401, text="bad key"))
    with pytest.raises(LLMError) as info:
        GroqProvider(api_key="k").complete("s", "u")
    assert not isinstance(info.value, RetryableError)


def test_missing_api_key_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(LLMError, match="GROQ_API_KEY"):
        GroqProvider()


def test_unknown_provider_is_rejected(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "nope")
    monkeypatch.setattr(llm, "_llm", None)
    with pytest.raises(LLMError, match="Unknown LLM_PROVIDER"):
        llm.get_llm()
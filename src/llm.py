"""LLM access: provider interface, disk cache, retry with backoff."""
import hashlib
import json
import os
import random
import sqlite3
import time
from abc import ABC, abstractmethod

import requests
from dotenv import load_dotenv

load_dotenv()  # reads .env into environment variables

CACHE_PATH = "llm_cache.sqlite"


class LLMError(Exception):
    """Permanent failure (bad key, bad request, retries exhausted)."""


class RetryableError(LLMError):
    """Temporary failure (rate limit, server error, network)."""

    def __init__(self, msg, retry_after=None):
        super().__init__(msg)
        self.retry_after = retry_after


class LLMProvider(ABC):
    name = "base"
    model = ""

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Return the model's text answer."""


class GroqProvider(LLMProvider):
    name = "groq"
    URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, model=None, api_key=None):
        self.model = model or os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise LLMError("GROQ_API_KEY is not set (put it in .env)")

    def complete(self, system, user):
        body = {
            "model": self.model,
            "temperature": 0,
            "max_completion_tokens": 1024,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if "gpt-oss" in self.model:
            body["reasoning_effort"] = "low"  # fewer hidden thinking tokens = cheaper
        try:
            r = requests.post(
                self.URL, json=body, timeout=60,
                headers={"Authorization": f"Bearer {self.api_key}"})
        except (requests.Timeout, requests.ConnectionError) as e:
            raise RetryableError(f"network problem: {e}")
        if r.status_code == 429 or r.status_code >= 500:
            ra = r.headers.get("retry-after")
            raise RetryableError(f"HTTP {r.status_code}: {r.text[:200]}",
                                 float(ra) if ra else None)
        if r.status_code != 200:
            raise LLMError(f"HTTP {r.status_code}: {r.text[:300]}")
        return r.json()["choices"][0]["message"]["content"] or ""


class CachedLLM:
    """Wraps a provider with an on-disk cache and retry/backoff."""

    def __init__(self, provider, cache_path=CACHE_PATH, max_retries=5):
        self.provider = provider
        self.max_retries = max_retries
        self.hits = 0
        self.misses = 0
        self.db = sqlite3.connect(cache_path)
        self.db.execute("CREATE TABLE IF NOT EXISTS cache "
                        "(key TEXT PRIMARY KEY, response TEXT, created REAL)")

    def _key(self, system, user):
        raw = json.dumps([self.provider.name, self.provider.model, system, user],
                         ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def complete(self, system, user):
        key = self._key(system, user)
        row = self.db.execute("SELECT response FROM cache WHERE key=?", (key,)).fetchone()
        if row:
            self.hits += 1
            return row[0]
        text = self._call_with_retry(system, user)
        self.db.execute("INSERT OR REPLACE INTO cache VALUES (?,?,?)",
                        (key, text, time.time()))
        self.db.commit()
        self.misses += 1
        return text

    def _call_with_retry(self, system, user):
        for attempt in range(self.max_retries):
            try:
                return self.provider.complete(system, user)
            except RetryableError as e:
                if attempt == self.max_retries - 1:
                    raise LLMError(f"gave up after {self.max_retries} attempts: {e}")
                wait = e.retry_after if e.retry_after is not None else min(2 ** attempt, 30)
                if wait > 120:  # e.g. daily quota used up: waiting is pointless
                    raise LLMError(f"asked to wait {wait:.0f}s, likely daily quota: {e}")
                wait += random.uniform(0, 1)  # jitter
                print(f"  [retry {attempt + 1}] waiting {wait:.1f}s ({str(e)[:80]})")
                time.sleep(wait)


_llm = None


def get_llm():
    """One shared CachedLLM for the whole app."""
    global _llm
    if _llm is None:
        name = os.getenv("LLM_PROVIDER", "groq").lower()
        if name != "groq":
            raise LLMError(f"Unknown LLM_PROVIDER '{name}'")
        _llm = CachedLLM(GroqProvider())
    return _llm
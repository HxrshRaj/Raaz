"""LLM provider abstraction: timeouts, bounded retries with exponential backoff, usage metrics.

The game never depends on a provider being present: `get_provider()` returns None when none is configured, and
callers fall back to the scripted dialogue mode (clearly labelled in the API response).
"""

from __future__ import annotations

import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

from .. import metrics
from ..config import get_settings
from ..logging_setup import get_logger

log = get_logger("raaz.llm")


class LLMError(Exception):
    def __init__(self, kind: str, message: str = ""):
        super().__init__(f"{kind}: {message}")
        self.kind = kind  # timeout | rate_limit | auth | bad_response | unavailable | bad_request

    @property
    def retryable(self) -> bool:
        return self.kind in ("timeout", "rate_limit", "unavailable")


@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    provider: str
    latency_s: float


class LLMProvider(ABC):
    name = "base"
    model = ""

    @abstractmethod
    def complete(self, system: str, messages: list[dict[str, str]], *, max_tokens: int, temperature: float,
                 timeout: float) -> LLMResult: ...


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str):
        import anthropic

        self._anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=api_key, max_retries=0)
        self.model = model

    def complete(self, system, messages, *, max_tokens, temperature, timeout):
        a = self._anthropic
        t0 = time.perf_counter()
        try:
            # `temperature` is deliberately not forwarded: current Claude models manage sampling themselves.
            r = self.client.messages.create(model=self.model, system=system, messages=messages, max_tokens=max_tokens,  # type: ignore[arg-type]
                                            timeout=timeout)
        except a.APITimeoutError as e:
            raise LLMError("timeout", str(e)) from e
        except a.RateLimitError as e:
            raise LLMError("rate_limit", str(e)) from e
        except a.AuthenticationError as e:
            raise LLMError("auth", "authentication failed") from e
        except a.BadRequestError as e:
            raise LLMError("bad_request", str(e)[:200]) from e
        except (a.APIConnectionError, a.InternalServerError) as e:
            raise LLMError("unavailable", str(e)[:200]) from e
        except a.APIError as e:
            raise LLMError("unavailable", str(e)[:200]) from e
        text = "".join(getattr(b, "text", "") for b in r.content)
        return LLMResult(text, r.usage.input_tokens, r.usage.output_tokens, self.model, self.name, time.perf_counter() - t0)


class OpenAICompatProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str, base_url: str | None):
        import openai

        self._openai = openai
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url, max_retries=0)
        self.model = model

    def complete(self, system, messages, *, max_tokens, temperature, timeout):
        o = self._openai
        t0 = time.perf_counter()
        msgs = [{"role": "system", "content": system}, *messages]
        try:
            try:
                r = self.client.chat.completions.create(model=self.model, messages=msgs, max_tokens=max_tokens,
                                                        temperature=temperature, timeout=timeout)
            except o.BadRequestError:
                r = self.client.chat.completions.create(model=self.model, messages=msgs, max_completion_tokens=max_tokens,
                                                        timeout=timeout)
        except o.APITimeoutError as e:
            raise LLMError("timeout", str(e)) from e
        except o.RateLimitError as e:
            raise LLMError("rate_limit", str(e)) from e
        except o.AuthenticationError as e:
            raise LLMError("auth", "authentication failed") from e
        except o.BadRequestError as e:
            raise LLMError("bad_request", str(e)[:200]) from e
        except o.APIError as e:
            raise LLMError("unavailable", str(e)[:200]) from e
        text = r.choices[0].message.content or ""
        u = r.usage
        return LLMResult(text, getattr(u, "prompt_tokens", 0) or 0, getattr(u, "completion_tokens", 0) or 0, self.model,
                         self.name, time.perf_counter() - t0)


class ScriptedProvider(LLMProvider):
    """Deterministic provider for automated tests. Never selected by configuration."""

    name = "scripted-test"
    model = "scripted"

    def __init__(self, responder):
        self.responder = responder
        self.calls: list[dict] = []

    def complete(self, system, messages, *, max_tokens, temperature, timeout):
        self.calls.append({"system": system, "messages": messages})
        out = self.responder(system, messages)
        if isinstance(out, Exception):
            raise out
        return LLMResult(out, len(system) // 4, len(out) // 4, self.model, self.name, 0.0)


_override: LLMProvider | None = None
_cached: tuple[tuple, LLMProvider | None] | None = None


def set_provider_for_tests(p: LLMProvider | None) -> None:
    global _override
    _override = p


def get_provider() -> LLMProvider | None:
    global _cached
    if _override is not None:
        return _override
    s = get_settings()
    key = (s.llm_provider, s.anthropic_api_key, s.anthropic_model, s.openai_api_key, s.openai_model, s.openai_base_url)
    if _cached and _cached[0] == key:
        return _cached[1]
    prov: LLMProvider | None = None
    try:
        if s.llm_provider == "anthropic" and s.anthropic_api_key:
            prov = AnthropicProvider(s.anthropic_api_key, s.anthropic_model)
        elif s.llm_provider == "openai" and (s.openai_api_key or s.openai_base_url):
            prov = OpenAICompatProvider(s.openai_api_key or "not-needed", s.openai_model, s.openai_base_url)
    except Exception as e:  # noqa: BLE001
        log.error("failed to initialise LLM provider", extra={"error": str(e)})
        prov = None
    _cached = (key, prov)
    return prov


def complete_with_retry(provider: LLMProvider, system: str, messages: list[dict[str, str]], *, max_tokens: int | None = None,
                        temperature: float = 0.7, purpose: str = "npc") -> LLMResult:
    s = get_settings()
    attempts = s.llm_max_retries + 1
    deadline = time.monotonic() + s.llm_timeout_s * attempts + 2
    last: LLMError | None = None
    for i in range(attempts):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            res = provider.complete(system, messages, max_tokens=max_tokens or s.llm_max_output_tokens,
                                    temperature=temperature, timeout=min(s.llm_timeout_s, remaining))
            metrics.inc("raaz_llm_calls_total", provider=provider.name, purpose=purpose, status="ok")
            metrics.inc("raaz_llm_tokens_total", res.input_tokens, provider=provider.name, direction="in")
            metrics.inc("raaz_llm_tokens_total", res.output_tokens, provider=provider.name, direction="out")
            metrics.observe("raaz_llm_latency_seconds", res.latency_s, provider=provider.name)
            if s.llm_cost_per_1k_in_usd or s.llm_cost_per_1k_out_usd:
                est = res.input_tokens / 1000 * s.llm_cost_per_1k_in_usd + res.output_tokens / 1000 * s.llm_cost_per_1k_out_usd
                metrics.inc("raaz_llm_estimated_cost_usd_total", est, provider=provider.name)  # ESTIMATE from configured rates
            return res
        except LLMError as e:
            last = e
            metrics.inc("raaz_llm_calls_total", provider=provider.name, purpose=purpose, status=e.kind)
            log.warning("llm call failed", extra={"kind": e.kind, "attempt": i + 1, "purpose": purpose})
            if not e.retryable or i == attempts - 1:
                break
            time.sleep(min(4.0, 0.5 * (2 ** i)) + random.uniform(0, 0.25))
    raise last or LLMError("unavailable", "no attempts made")

import json
from dataclasses import asdict

import httpx
import pytest

from b3desk.data import load
from b3desk.providers import Narrator, debate
from b3desk.research import snapshot


@pytest.mark.parametrize(
    "provider,response",
    [
        ("openai", {"choices": [{"message": {"content": "Research commentary"}}]}),
        ("anthropic", {"content": [{"type": "text", "text": "Research commentary"}]}),
        ("ollama", {"message": {"content": "Research commentary"}}),
    ],
)
def test_provider_contracts_cannot_mutate_allocations(monkeypatch, provider, response):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    evidence = snapshot(load(), 100)
    before = asdict(evidence)
    requests = []

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        assert body["model"] == "explicit-test-model"
        if provider == "anthropic":
            assert request.headers["anthropic-version"] == "2023-06-01"
        if provider == "ollama":
            assert body["stream"] is False
        return httpx.Response(200, json=response)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        transcript = debate(evidence, provider, "explicit-test-model", client=client)
    assert len(transcript) == len(requests) == 7
    assert asdict(evidence) == before
    assert "prior_commentary_untrusted" in requests[-1]["messages"][-1]["content"]


def test_offline_needs_no_network(monkeypatch):
    monkeypatch.setattr(httpx.Client, "post", lambda *a, **k: pytest.fail("network used"))
    assert len(debate(snapshot(load(), 100))) == 7


def test_provider_error_does_not_echo_secret(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(401, text="test-secret"))
    ) as client:
        with pytest.raises(ValueError, match="narration failed") as error:
            Narrator("openai", "test", client).say("test")
    assert "test-secret" not in str(error.value)

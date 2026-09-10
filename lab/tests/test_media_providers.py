"""
Tests de CloudflareFluxProvider -- construccion del request, headers,
autenticacion, seleccion de modelo, manejo de errores y respuestas
invalidas. Cero llamadas reales: requests.post se mockea siempre.
"""

import base64
import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from lab.media.providers.cloudflare_flux import CloudflareFluxProvider

FAKE_PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def _make_provider(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acc123")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "token-secret-abc")
    return CloudflareFluxProvider(model="@cf/black-forest-labs/flux-1-schnell")


def _fake_response(status_code=200, json_body=None, text=""):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.text = text or (json.dumps(json_body) if json_body is not None else "")
    if json_body is not None:
        resp.json.return_value = json_body
    else:
        resp.json.side_effect = ValueError("no json")
    return resp


def _success_payload(b64=None):
    return {
        "result": {"image": b64 or base64.b64encode(FAKE_PNG_1X1).decode("ascii")},
        "success": True,
        "errors": [],
        "messages": [],
    }


# --- construccion del request ---------------------------------------------

def test_missing_credentials_raises_before_any_request(monkeypatch):
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="CLOUDFLARE_ACCOUNT_ID"):
        CloudflareFluxProvider(model="@cf/black-forest-labs/flux-1-schnell")


def test_request_url_and_auth_header(monkeypatch):
    provider = _make_provider(monkeypatch)
    with patch("lab.media.providers.cloudflare_flux.requests.post") as mock_post:
        mock_post.return_value = _fake_response(200, _success_payload())
        provider.generate("a cat", aspect_ratio="1:1")

    args, kwargs = mock_post.call_args
    assert args[0] == "https://api.cloudflare.com/client/v4/accounts/acc123/ai/run/@cf/black-forest-labs/flux-1-schnell"
    assert kwargs["headers"] == {"Authorization": "Bearer token-secret-abc"}
    assert "Content-Type" not in kwargs.get("headers", {})  # requests arma el boundary solo


def test_generate_without_references_sends_plain_json(monkeypatch):
    """flux-1-schnell no acepta multipart ni width/height (confirmado contra la
    documentación oficial) -- generate() sin referencias debe mandar un body
    JSON plano con solo prompt+steps."""
    provider = _make_provider(monkeypatch)
    with patch("lab.media.providers.cloudflare_flux.requests.post") as mock_post:
        mock_post.return_value = _fake_response(200, _success_payload())
        provider.generate("a cat sitting on a wall", aspect_ratio="9:16")

    kwargs = mock_post.call_args.kwargs
    assert "files" not in kwargs
    assert kwargs["json"] == {"prompt": "a cat sitting on a wall", "steps": 4}


def test_default_steps_matches_cloudflare_documented_default(monkeypatch):
    provider = _make_provider(monkeypatch)
    with patch("lab.media.providers.cloudflare_flux.requests.post") as mock_post:
        mock_post.return_value = _fake_response(200, _success_payload())
        provider.generate("x", aspect_ratio="1:1")
    assert mock_post.call_args.kwargs["json"]["steps"] == 4


def test_generate_with_references_uses_input_image_fields(monkeypatch):
    provider = _make_provider(monkeypatch)
    with patch("lab.media.providers.cloudflare_flux.requests.post") as mock_post:
        mock_post.return_value = _fake_response(200, _success_payload())
        provider.generate("style transfer", aspect_ratio="1:1", references=[FAKE_PNG_1X1, FAKE_PNG_1X1])

    files = mock_post.call_args.kwargs["files"]
    assert "input_image_0" in files
    assert "input_image_1" in files
    assert files["input_image_0"][1] == FAKE_PNG_1X1


def test_edit_puts_base_image_as_input_image_0(monkeypatch):
    provider = _make_provider(monkeypatch)
    with patch("lab.media.providers.cloudflare_flux.requests.post") as mock_post:
        mock_post.return_value = _fake_response(200, _success_payload())
        provider.edit(FAKE_PNG_1X1, "make it blue", aspect_ratio="1:1")

    files = mock_post.call_args.kwargs["files"]
    assert files["input_image_0"][1] == FAKE_PNG_1X1
    assert not any(k.startswith("input_image_1") for k in files)


def test_generate_from_references_requires_at_least_one(monkeypatch):
    provider = _make_provider(monkeypatch)
    with pytest.raises(ValueError, match="al menos una referencia"):
        provider.generate_from_references("a cat", [], aspect_ratio="1:1")


def test_more_than_four_images_raises_without_calling_api(monkeypatch):
    provider = _make_provider(monkeypatch)
    with patch("lab.media.providers.cloudflare_flux.requests.post") as mock_post:
        with pytest.raises(ValueError, match="hasta 4"):
            provider.generate_from_references("x", [FAKE_PNG_1X1] * 5, aspect_ratio="1:1")
    mock_post.assert_not_called()


def test_unknown_aspect_ratio_falls_back_to_default(monkeypatch):
    # width/height solo se envían por el camino multipart (modelos
    # multi-referencia) -- generate() sin referencias (flux-1-schnell) no los
    # manda en absoluto (ver test_generate_without_references_sends_plain_json).
    provider = _make_provider(monkeypatch)
    with patch("lab.media.providers.cloudflare_flux.requests.post") as mock_post:
        mock_post.return_value = _fake_response(200, _success_payload())
        provider.generate_from_references("x", [FAKE_PNG_1X1], aspect_ratio="21:9")
    files = mock_post.call_args.kwargs["files"]
    assert files["width"] == (None, "1024")
    assert files["height"] == (None, "1024")


# --- respuesta valida -------------------------------------------------------

def test_successful_response_decodes_image_and_metadata(monkeypatch):
    provider = _make_provider(monkeypatch)
    with patch("lab.media.providers.cloudflare_flux.requests.post") as mock_post:
        mock_post.return_value = _fake_response(200, _success_payload())
        result = provider.generate("a cat", aspect_ratio="1:1")

    assert result.image_bytes == FAKE_PNG_1X1
    assert result.mime_type == "image/png"
    assert result.model == "@cf/black-forest-labs/flux-1-schnell"


# --- manejo de errores HTTP --------------------------------------------------

@pytest.mark.parametrize("status", [401, 403, 404, 429, 500])
def test_http_error_statuses_raise_clear_errors_without_leaking_token(monkeypatch, status):
    provider = _make_provider(monkeypatch)
    with patch("lab.media.providers.cloudflare_flux.requests.post") as mock_post:
        mock_post.return_value = _fake_response(status, text="some error body")
        with pytest.raises(RuntimeError) as excinfo:
            provider.generate("x", aspect_ratio="1:1")
    assert "token-secret-abc" not in str(excinfo.value)


def test_timeout_raises_clear_error(monkeypatch):
    provider = _make_provider(monkeypatch)
    with patch("lab.media.providers.cloudflare_flux.requests.post", side_effect=requests.Timeout("timed out")):
        with pytest.raises(RuntimeError, match="timeout"):
            provider.generate("x", aspect_ratio="1:1")


def test_network_error_raises_clear_error(monkeypatch):
    provider = _make_provider(monkeypatch)
    with patch("lab.media.providers.cloudflare_flux.requests.post", side_effect=requests.ConnectionError("no network")):
        with pytest.raises(RuntimeError, match="error de red"):
            provider.generate("x", aspect_ratio="1:1")


# --- respuestas malformadas --------------------------------------------------

def test_invalid_json_response_raises(monkeypatch):
    provider = _make_provider(monkeypatch)
    with patch("lab.media.providers.cloudflare_flux.requests.post") as mock_post:
        mock_post.return_value = _fake_response(200, json_body=None, text="not json")
        with pytest.raises(RuntimeError, match="JSON válido"):
            provider.generate("x", aspect_ratio="1:1")


def test_success_false_raises_with_errors_in_message(monkeypatch):
    provider = _make_provider(monkeypatch)
    payload = {"result": None, "success": False, "errors": [{"code": 5007, "message": "bad prompt"}], "messages": []}
    with patch("lab.media.providers.cloudflare_flux.requests.post") as mock_post:
        mock_post.return_value = _fake_response(200, payload)
        with pytest.raises(RuntimeError, match="bad prompt"):
            provider.generate("x", aspect_ratio="1:1")


def test_missing_result_image_raises(monkeypatch):
    provider = _make_provider(monkeypatch)
    payload = {"result": {}, "success": True, "errors": [], "messages": []}
    with patch("lab.media.providers.cloudflare_flux.requests.post") as mock_post:
        mock_post.return_value = _fake_response(200, payload)
        with pytest.raises(RuntimeError, match="result.image"):
            provider.generate("x", aspect_ratio="1:1")


def test_malformed_base64_raises(monkeypatch):
    provider = _make_provider(monkeypatch)
    payload = {"result": {"image": "!!!not-base64!!!"}, "success": True, "errors": [], "messages": []}
    with patch("lab.media.providers.cloudflare_flux.requests.post") as mock_post:
        mock_post.return_value = _fake_response(200, payload)
        with pytest.raises(RuntimeError, match="base64"):
            provider.generate("x", aspect_ratio="1:1")


def test_empty_decoded_image_raises(monkeypatch):
    provider = _make_provider(monkeypatch)
    payload = {"result": {"image": ""}, "success": True, "errors": [], "messages": []}
    with patch("lab.media.providers.cloudflare_flux.requests.post") as mock_post:
        mock_post.return_value = _fake_response(200, payload)
        with pytest.raises(RuntimeError, match="result.image"):
            provider.generate("x", aspect_ratio="1:1")

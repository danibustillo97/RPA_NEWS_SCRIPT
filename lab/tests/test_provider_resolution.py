"""
Tests de lab.media.providers.resolver -- seleccion de provider por nombre/env,
aislamiento entre providers, y que Gemini sigue resolviendo despues de
agregar Cloudflare (sin gastar ninguna cuota real: solo construccion).
"""

import pytest

from lab.media.providers.cloudflare_flux import CloudflareFluxProvider
from lab.media.providers.gemini_image import GeminiImageProvider
from lab.media.providers.resolver import resolve_media_provider


def test_resolve_gemini_by_name(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    provider = resolve_media_provider("gemini")
    assert isinstance(provider, GeminiImageProvider)
    assert provider.name == "gemini"


def test_resolve_cloudflare_by_name(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "fake-account-id")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "fake-token")
    provider = resolve_media_provider("cloudflare")
    assert isinstance(provider, CloudflareFluxProvider)
    assert provider.name == "cloudflare"
    assert provider.model == "@cf/black-forest-labs/flux-1-schnell"


def test_cloudflare_provider_uses_explicit_model_param(monkeypatch):
    # settings.CLOUDFLARE_IMAGE_MODEL se cachea al importar lab.config.settings
    # (mismo patron que GEMINI_IMAGE_MODEL) -- monkeypatchear el env var a mitad
    # de sesion no lo cambia, por eso este test verifica la selección de modelo
    # contra el constructor del provider directamente, no contra el resolver.
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "fake-account-id")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "fake-token")
    provider = CloudflareFluxProvider(model="@cf/black-forest-labs/flux-1-schnell")
    assert provider.model == "@cf/black-forest-labs/flux-1-schnell"


def test_resolve_unknown_provider_raises():
    with pytest.raises(ValueError, match="Provider de media desconocido"):
        resolve_media_provider("bogus-provider")


def test_resolve_default_reads_env_var(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.setenv("LAB_MEDIA_PROVIDER", "gemini")
    assert isinstance(resolve_media_provider(), GeminiImageProvider)

    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "fake-account-id")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "fake-token")
    monkeypatch.setenv("LAB_MEDIA_PROVIDER", "cloudflare")
    assert isinstance(resolve_media_provider(), CloudflareFluxProvider)


def test_explicit_name_overrides_env_default(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "fake-account-id")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "fake-token")
    monkeypatch.setenv("LAB_MEDIA_PROVIDER", "cloudflare")
    assert isinstance(resolve_media_provider("gemini"), GeminiImageProvider)


def test_gemini_construction_does_not_require_cloudflare_vars(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    provider = resolve_media_provider("gemini")
    assert isinstance(provider, GeminiImageProvider)


def test_cloudflare_construction_does_not_require_gemini_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "fake-account-id")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "fake-token")
    provider = resolve_media_provider("cloudflare")
    assert isinstance(provider, CloudflareFluxProvider)


def test_gemini_missing_key_raises_clear_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        resolve_media_provider("gemini")


def test_cloudflare_missing_credentials_raises_clear_error(monkeypatch):
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="CLOUDFLARE_ACCOUNT_ID"):
        resolve_media_provider("cloudflare")

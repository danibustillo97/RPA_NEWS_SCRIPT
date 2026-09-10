"""
Tests de lab.media.registry -- requested_aspect_ratio vs actual_aspect_ratio.

Deuda técnica cerrada: el registro confundía la intención de generación
(lo pedido en el prompt_spec) con la forma física real del archivo. Un
provider como flux-1-schnell puede ignorar por completo el aspect_ratio
pedido (siempre produce 1024x1024) -- el Asset Registry nunca debe afirmar
que el archivo es 9:16 si width/height reales dicen 1:1.

Usa una historia descartable (story_id de prueba, limpiada en cada test) --
no toca datos reales de ninguna historia existente en el workspace.
"""

import shutil

import pytest

from lab.media import registry
from lab.media.paths import story_media_dir

_TEST_STORY_ID = "_test_aspect_ratio_story"


@pytest.fixture(autouse=True)
def _clean_test_story():
    shutil.rmtree(story_media_dir(_TEST_STORY_ID), ignore_errors=True)
    yield
    shutil.rmtree(story_media_dir(_TEST_STORY_ID), ignore_errors=True)


def _register(*, width, height, requested_aspect_ratio, asset_id="img_001"):
    return registry.register_asset(
        _TEST_STORY_ID,
        asset_id=asset_id,
        scene_id="scene_01",
        type_="image",
        subtype="generated",
        filename=f"{asset_id}.jpeg",
        relative_path=f"images/generated/{asset_id}.jpeg",
        mime_type="image/jpeg",
        width=width,
        height=height,
        requested_aspect_ratio=requested_aspect_ratio,
        source=None,
        provider="cloudflare",
        model="@cf/black-forest-labs/flux-1-schnell",
        prompt_version=1,
        parent_asset_id=None,
        references=[],
        provenance="AI_GENERATED",
        status="READY",
    )


def test_requested_9_16_but_output_1024x1024_records_actual_1_1():
    """Caso real: se pide 9:16, flux-1-schnell entrega 1024x1024."""
    record = _register(width=1024, height=1024, requested_aspect_ratio="9:16")
    assert record["requested_aspect_ratio"] == "9:16"
    assert record["actual_aspect_ratio"] == "1:1"
    assert record["requested_aspect_ratio"] != record["actual_aspect_ratio"]


def test_requested_1_1_and_output_1024x1024_both_match():
    record = _register(width=1024, height=1024, requested_aspect_ratio="1:1")
    assert record["requested_aspect_ratio"] == "1:1"
    assert record["actual_aspect_ratio"] == "1:1"


def test_width_height_always_reflect_real_file_dimensions():
    """width/height nunca se ajustan para "coincidir" con lo pedido -- quedan
    tal cual el archivo real, aunque difieran de requested_aspect_ratio."""
    record = _register(width=1024, height=1024, requested_aspect_ratio="16:9")
    assert record["width"] == 1024
    assert record["height"] == 1024


def test_registry_never_records_9_16_as_actual_when_file_is_square():
    record = _register(width=1024, height=1024, requested_aspect_ratio="9:16")
    assert record["actual_aspect_ratio"] != "9:16"
    all_records = registry.list_assets(_TEST_STORY_ID)
    assert all(r["actual_aspect_ratio"] != "9:16" for r in all_records if r["width"] == r["height"])


def test_actual_aspect_ratio_is_derived_not_trusted_from_request():
    """Aunque requested_aspect_ratio diga cualquier cosa, actual_aspect_ratio
    sale exclusivamente de width/height reales (576x1024 -> 9:16 real)."""
    record = _register(width=576, height=1024, requested_aspect_ratio="1:1")
    assert record["actual_aspect_ratio"] == "9:16"
    assert record["requested_aspect_ratio"] == "1:1"


def test_missing_dimensions_never_fabricates_actual_aspect_ratio():
    record = _register(width=None, height=None, requested_aspect_ratio="9:16")
    assert record["actual_aspect_ratio"] is None


def test_old_ambiguous_aspect_ratio_field_no_longer_written():
    record = _register(width=1024, height=1024, requested_aspect_ratio="9:16")
    assert "aspect_ratio" not in record

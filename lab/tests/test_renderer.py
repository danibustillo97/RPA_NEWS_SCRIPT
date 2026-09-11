"""
Tests de lab.render.renderer -- Fase 4.2 etapa 5. Primer modulo de LAB que
ejecuta FFmpeg real: estos tests corren el binario de verdad (mismo criterio
"no mockear lo que se puede probar real" del resto de LAB) contra una imagen
PNG minuscula generada con Pillow en el propio test -- rapido, local, sin red.

_build_filter() se prueba aparte como funcion pura (sin FFmpeg). El resto
ejercita process_render_plan() de punta a punta: construye un render_plan.json
real (via init_render_plan, Etapa 3, sin cambios) y corre el Renderer sobre el.
"""

import hashlib
import shutil

import pytest

from lab.animation.planner import init_animation_plan
from lab.media.blueprint import init_blueprint
from lab.media.paths import asset_registry_path, sequence_path, story_media_dir
from lab.media.registry import register_asset
from lab.render.paths import render_plan_path, rendered_video_path
from lab.render.planner import init_render_plan, load as load_render_plan
from lab.render.renderer import _build_filter, process_render_plan
from lab.sequence.planner import init_sequence

_TEST_STORY_ID = "_test_renderer_story"


@pytest.fixture(autouse=True)
def _clean_test_story():
    shutil.rmtree(story_media_dir(_TEST_STORY_ID), ignore_errors=True)
    yield
    shutil.rmtree(story_media_dir(_TEST_STORY_ID), ignore_errors=True)


def _sequence_shot(**overrides):
    shot = {
        "shot_id": "shot_01", "scene_id": "scene_01", "asset_id": None,
        "order": 1, "duration_seconds": 1.0, "framing": "test",
        "motion": "STATIC", "transition_in": "NONE", "transition_out": "CUT",
        "purpose": "hook", "notes": "",
        "transform_required": None, "suggested_transform": None,
    }
    shot.update(overrides)
    return shot


def _setup_animation_plan(shots, target_aspect_ratio="9:16"):
    """Blueprint + sequence + animation_plan -- NO registra assets (eso lo
    hace cada test antes de llamar a esto, ya que init_render_plan() sí
    necesita las dimensiones reales del asset ya registradas)."""
    scene_ids = sorted({s["scene_id"] for s in shots})
    init_blueprint(
        _TEST_STORY_ID, visual_identity={"style_id": "test"}, characters=[], references=[],
        scenes=[{"scene_id": sid, "media_requirement": {"scene_id": sid}} for sid in scene_ids],
    )
    init_sequence(
        _TEST_STORY_ID, sequence_id="seq_001", target_format="REEL", target_aspect_ratio=target_aspect_ratio,
        narrative_structure="HOOK -> CLOSING", shots=shots,
    )
    return init_animation_plan(_TEST_STORY_ID)


def _register_real_asset(asset_id, width=64, height=64):
    """Registra el asset Y escribe un PNG real y decodificable en el path
    esperado -- FFmpeg necesita un archivo de verdad, no solo el registro."""
    from PIL import Image

    relative_path = f"images/generated/{asset_id}.png"
    absolute_path = story_media_dir(_TEST_STORY_ID) / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (width, height), color=(90, 130, 200)).save(absolute_path, format="PNG")

    return register_asset(
        _TEST_STORY_ID, asset_id=asset_id, scene_id="scene_02", type_="image", subtype="generated",
        filename=f"{asset_id}.png", relative_path=relative_path,
        mime_type="image/png", width=width, height=height, requested_aspect_ratio="9:16",
        source=None, provider="cloudflare", model="@cf/black-forest-labs/flux-1-schnell",
        prompt_version=1, parent_asset_id=None, references=[], provenance="AI_GENERATED", status="READY",
    )


# --- _build_filter (funcion pura, sin FFmpeg) --------------------------------

def test_build_filter_no_transform_scales_to_target():
    shot = {"transform_geometry": None}
    assert _build_filter(shot, 1080, 1920) == "scale=1080:1920"


def test_build_filter_pad_matches_real_extend_case():
    # Mismos numeros que el caso real verificado en Etapa 3 (1024x1024 -> 9:16).
    shot = {"transform_geometry": {
        "type": "EXTEND", "computable": True, "operation": "PAD",
        "scaled_width": 1080, "scaled_height": 1080,
        "pad_left": 0, "pad_right": 0, "pad_top": 420, "pad_bottom": 420,
    }}
    assert _build_filter(shot, 1080, 1920) == "scale=1080:1080,pad=1080:1920:0:420:color=black"


def test_build_filter_crop():
    shot = {"transform_geometry": {
        "type": "CROP", "computable": True, "operation": "CROP",
        "scaled_width": 1920, "scaled_height": 1920,
        "crop_left": 0, "crop_right": 0, "crop_top": 420, "crop_bottom": 420,
    }}
    assert _build_filter(shot, 1920, 1080) == "scale=1920:1920,crop=1920:1080:0:420"


def test_build_filter_not_computable_raises():
    shot = {"render_shot_id": "render_shot_02", "transform_geometry": {"type": "COMPOSE", "computable": False}}
    with pytest.raises(ValueError, match="no computable"):
        _build_filter(shot, 1080, 1920)


# --- process_render_plan (FFmpeg real) ---------------------------------------

def test_process_render_plan_no_render_plan_raises():
    with pytest.raises(ValueError, match="render_plan"):
        process_render_plan(_TEST_STORY_ID)


def test_process_render_plan_renders_eligible_shot_with_real_ffmpeg():
    _setup_animation_plan([
        _sequence_shot(shot_id="shot_01", scene_id="scene_01", order=1),
        _sequence_shot(
            shot_id="shot_02", scene_id="scene_02", order=2, asset_id="img_001",
            motion="SLOW_ZOOM_IN", transform_required=True, suggested_transform="EXTEND",
        ),
    ])
    # El asset debe existir ANTES de init_render_plan() -- necesita sus
    # dimensiones reales para calcular la geometría (mismo orden que Etapa 4).
    _register_real_asset("img_001")
    init_render_plan(_TEST_STORY_ID)

    results = process_render_plan(_TEST_STORY_ID)

    shot_01_result = next(r for r in results if r["render_shot_id"] == "render_shot_01")
    assert shot_01_result["status"] == "PENDING"
    assert shot_01_result["reason"] == "sin asset (texto-only)"

    shot_02_result = next(r for r in results if r["render_shot_id"] == "render_shot_02")
    assert shot_02_result["status"] == "DONE", shot_02_result.get("error")
    assert shot_02_result["output_path"] == "videos/rendered/render_shot_02.mp4"

    output_file = rendered_video_path(_TEST_STORY_ID, "render_shot_02")
    assert output_file.exists()
    assert output_file.stat().st_size > 0

    plan = load_render_plan(_TEST_STORY_ID)
    shot_02 = next(s for s in plan["shots"] if s["render_shot_id"] == "render_shot_02")
    assert shot_02["status"] == "DONE"
    assert shot_02["output_path"] == "videos/rendered/render_shot_02.mp4"
    assert shot_02["error"] is None

    shot_01 = next(s for s in plan["shots"] if s["render_shot_id"] == "render_shot_01")
    assert shot_01["status"] == "PENDING"
    assert "output_path" not in shot_01


def test_process_render_plan_single_shot_id_only_processes_that_shot():
    _setup_animation_plan([
        _sequence_shot(shot_id="shot_01", scene_id="scene_01", order=1, asset_id="img_001"),
        _sequence_shot(shot_id="shot_02", scene_id="scene_02", order=2, asset_id="img_002"),
    ])
    _register_real_asset("img_001")
    _register_real_asset("img_002")
    init_render_plan(_TEST_STORY_ID)

    results = process_render_plan(_TEST_STORY_ID, render_shot_id="render_shot_01")

    assert len(results) == 1
    assert results[0]["render_shot_id"] == "render_shot_01"
    assert results[0]["status"] == "DONE"

    plan = load_render_plan(_TEST_STORY_ID)
    shot_02 = next(s for s in plan["shots"] if s["render_shot_id"] == "render_shot_02")
    assert shot_02["status"] == "PENDING"  # no tocado -- no se pidió


def test_process_render_plan_unknown_shot_id_raises():
    _setup_animation_plan([_sequence_shot()])
    init_render_plan(_TEST_STORY_ID)
    with pytest.raises(ValueError, match="no encontrado"):
        process_render_plan(_TEST_STORY_ID, render_shot_id="render_shot_no_existe")


def test_process_render_plan_missing_asset_file_fails_shot_without_crashing():
    # Asset registrado pero sin archivo real en disco -- FFmpeg debe fallar
    # ese shot puntual (status FAILED, error capturado), no lanzar.
    _setup_animation_plan([
        _sequence_shot(shot_id="shot_01", scene_id="scene_01", order=1, asset_id="img_001"),
    ])
    register_asset(
        _TEST_STORY_ID, asset_id="img_001", scene_id="scene_01", type_="image", subtype="generated",
        filename="img_001.png", relative_path="images/generated/img_001.png",
        mime_type="image/png", width=64, height=64, requested_aspect_ratio="9:16",
        source=None, provider="cloudflare", model="@cf/black-forest-labs/flux-1-schnell",
        prompt_version=1, parent_asset_id=None, references=[], provenance="AI_GENERATED", status="READY",
    )
    init_render_plan(_TEST_STORY_ID)

    results = process_render_plan(_TEST_STORY_ID)

    assert results[0]["status"] == "FAILED"
    assert results[0]["error"]


def test_process_render_plan_does_not_modify_upstream_artifacts():
    _setup_animation_plan([
        _sequence_shot(shot_id="shot_01", scene_id="scene_01", order=1, asset_id="img_001",
                       transform_required=True, suggested_transform="EXTEND"),
    ])
    _register_real_asset("img_001")
    init_render_plan(_TEST_STORY_ID)

    def h(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    seq_before = h(sequence_path(_TEST_STORY_ID))
    registry_before = h(asset_registry_path(_TEST_STORY_ID))
    from lab.animation.paths import animation_plan_path
    anim_before = h(animation_plan_path(_TEST_STORY_ID))

    process_render_plan(_TEST_STORY_ID)

    assert h(sequence_path(_TEST_STORY_ID)) == seq_before
    assert h(asset_registry_path(_TEST_STORY_ID)) == registry_before
    assert h(animation_plan_path(_TEST_STORY_ID)) == anim_before
    # render_plan.json SI cambia -- es su propio artifact, por diseño.
    assert render_plan_path(_TEST_STORY_ID).exists()

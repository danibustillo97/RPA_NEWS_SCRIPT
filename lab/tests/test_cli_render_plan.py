"""
Tests de integracion del comando CLI `lab.cli render-plan` (Fase 4.2 etapa 4)
-- el wrapper fino que la skill lab-render-planning invoca. No vuelve a probar
las reglas de validacion (eso ya lo cubre test_render_planner.py, 24 tests
contra lab.render.planner directamente) -- solo que el comando CLI conecta
esa capa correctamente: llama al planner real, registra el job, imprime el
resumen esperado, y nunca toca animation_plan.json/sequence.json/asset_registry.json.
"""

import argparse
import json
import shutil
from unittest.mock import patch

import pytest

import lab.cli as cli
from lab.animation.paths import animation_plan_path
from lab.animation.planner import init_animation_plan
from lab.core.paths import JOBS_DONE_DIR, JOBS_FAILED_DIR
from lab.media.blueprint import init_blueprint
from lab.media.paths import asset_registry_path, sequence_path, story_media_dir
from lab.media.registry import register_asset
from lab.sequence.planner import init_sequence

_TEST_STORY_ID = "_test_cli_render_story"


@pytest.fixture(autouse=True)
def _clean_test_story():
    # Primer archivo que ejercita record_job() para render_plan -- sin este
    # cleanup, cada corrida de tests dejaria archivos de job reales
    # acumulandose en lab/jobs/done|failed/.
    shutil.rmtree(story_media_dir(_TEST_STORY_ID), ignore_errors=True)
    jobs_before = {p.name for p in JOBS_DONE_DIR.glob("*.json")} | {p.name for p in JOBS_FAILED_DIR.glob("*.json")}
    yield
    shutil.rmtree(story_media_dir(_TEST_STORY_ID), ignore_errors=True)
    for jobs_dir in (JOBS_DONE_DIR, JOBS_FAILED_DIR):
        for path in jobs_dir.glob("*.json"):
            if path.name not in jobs_before:
                path.unlink()


def _sequence_shot(**overrides):
    shot = {
        "shot_id": "shot_01", "scene_id": "scene_01", "asset_id": None,
        "order": 1, "duration_seconds": 3.0, "framing": "test",
        "motion": "STATIC", "transition_in": "NONE", "transition_out": "CUT",
        "purpose": "hook", "notes": "",
        "transform_required": None, "suggested_transform": None,
    }
    shot.update(overrides)
    return shot


def _setup_animation_plan(shots, target_aspect_ratio="9:16"):
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


def _register_asset(asset_id):
    return register_asset(
        _TEST_STORY_ID, asset_id=asset_id, scene_id="scene_02", type_="image", subtype="generated",
        filename=f"{asset_id}.jpeg", relative_path=f"images/generated/{asset_id}.jpeg",
        mime_type="image/jpeg", width=1024, height=1024, requested_aspect_ratio="9:16",
        source=None, provider="cloudflare", model="@cf/black-forest-labs/flux-1-schnell",
        prompt_version=1, parent_asset_id=None, references=[], provenance="AI_GENERATED", status="READY",
    )


def _run_render_plan(story_id=_TEST_STORY_ID):
    return cli.cmd_render_plan(argparse.Namespace(story_id=story_id))


def _capture_stdout(fn):
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn()
    return buf.getvalue()


def test_cmd_render_plan_missing_animation_plan_returns_1(capsys):
    exit_code = _run_render_plan()
    assert exit_code == 1
    out = json.loads(capsys.readouterr().out)
    assert "error" in out


def test_cmd_render_plan_success_returns_0_and_prints_summary(capsys):
    _setup_animation_plan([
        _sequence_shot(shot_id="shot_01", scene_id="scene_01", order=1),
        _sequence_shot(
            shot_id="shot_02", scene_id="scene_02", order=2, asset_id="img_001",
            motion="SLOW_ZOOM_IN", transform_required=True, suggested_transform="EXTEND",
        ),
    ])
    # El Render Planner (a diferencia del Animation Planner) sí necesita las
    # dimensiones reales del asset -- se registra después de armar el
    # animation plan, antes de correr el comando render-plan.
    _register_asset("img_001")

    exit_code = _run_render_plan()
    assert exit_code == 0

    out = json.loads(capsys.readouterr().out)
    assert out["story_id"] == _TEST_STORY_ID
    assert out["animation_plan_id"] == "anim_001"
    assert out["target_aspect_ratio"] == "9:16"
    assert out["target_width"] == 1080
    assert out["target_height"] == 1920
    assert out["total_shots"] == 2
    assert out["validation_errors"] == []
    assert out["status"] == "DRAFT"

    shot_02 = next(s for s in out["shots"] if s["shot_id"] == "shot_02")
    assert shot_02["asset_id"] == "img_001"
    assert shot_02["backend"] == "FFMPEG_LOCAL"
    assert shot_02["status"] == "PENDING"
    geometry = shot_02["transform_geometry"]
    assert geometry["type"] == "EXTEND"
    assert geometry["computable"] is True
    assert geometry["scaled_width"] == 1080
    assert geometry["scaled_height"] == 1080
    assert geometry["pad_top"] == 420
    assert geometry["pad_bottom"] == 420
    assert geometry["pad_left"] == 0
    assert geometry["pad_right"] == 0

    shot_01 = next(s for s in out["shots"] if s["shot_id"] == "shot_01")
    assert shot_01["transform_geometry"] is None


def test_cmd_render_plan_records_job():
    _setup_animation_plan([_sequence_shot()])
    out_job_id = json.loads(_capture_stdout(_run_render_plan))["job_id"]

    job_path = JOBS_DONE_DIR / f"{out_job_id}.json"
    assert job_path.exists()
    job = json.loads(job_path.read_text(encoding="utf-8"))
    assert job["type"] == "render_plan"
    assert job["status"] == "done"
    assert job["params"]["story_id"] == _TEST_STORY_ID


def test_cmd_render_plan_validation_errors_return_1_and_job_failed(capsys):
    _setup_animation_plan([_sequence_shot()])
    with patch("lab.render.planner.validate_render_plan", return_value=["error ficticio de prueba"]):
        exit_code = _run_render_plan()
    assert exit_code == 1
    out = json.loads(capsys.readouterr().out)
    assert out["validation_errors"] == ["error ficticio de prueba"]


def test_cmd_render_plan_does_not_modify_animation_plan_sequence_or_registry():
    _setup_animation_plan([
        _sequence_shot(asset_id="img_001", transform_required=True, suggested_transform="CROP"),
    ])
    _register_asset("img_001")

    anim_plan_before = animation_plan_path(_TEST_STORY_ID).read_bytes()
    seq_before = sequence_path(_TEST_STORY_ID).read_bytes()
    registry_before = asset_registry_path(_TEST_STORY_ID).read_bytes()

    _run_render_plan()

    assert animation_plan_path(_TEST_STORY_ID).read_bytes() == anim_plan_before
    assert sequence_path(_TEST_STORY_ID).read_bytes() == seq_before
    assert asset_registry_path(_TEST_STORY_ID).read_bytes() == registry_before

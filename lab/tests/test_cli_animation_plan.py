"""
Tests de integracion del comando CLI `lab.cli animation-plan` (Fase 4.2
etapa 2) -- el wrapper fino que la skill lab-animation-planning invoca.
No vuelve a probar las 10 reglas de validacion (eso ya lo cubre
test_animation_planner.py, 28 tests contra lab.animation.planner
directamente) -- solo que el comando CLI conecta esa capa correctamente:
llama al planner real, registra el job, imprime el resumen esperado, y
nunca toca sequence.json/asset_registry.json.
"""

import argparse
import json
import shutil
from unittest.mock import patch

import pytest

import lab.cli as cli
from lab.core.paths import JOBS_DONE_DIR, JOBS_FAILED_DIR
from lab.media.blueprint import init_blueprint
from lab.media.paths import asset_registry_path, sequence_path, story_media_dir
from lab.media.registry import register_asset
from lab.sequence.planner import init_sequence

_TEST_STORY_ID = "_test_cli_animation_story"


@pytest.fixture(autouse=True)
def _clean_test_story():
    # Este archivo es el primero en la suite que ejercita record_job() de
    # verdad (via cmd_animation_plan) -- sin este cleanup, cada corrida de
    # tests dejaria archivos de job reales acumulandose en lab/jobs/done|failed/.
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


def _setup_sequence(shots):
    scene_ids = sorted({s["scene_id"] for s in shots})
    init_blueprint(
        _TEST_STORY_ID, visual_identity={"style_id": "test"}, characters=[], references=[],
        scenes=[{"scene_id": sid, "media_requirement": {"scene_id": sid}} for sid in scene_ids],
    )
    return init_sequence(
        _TEST_STORY_ID, sequence_id="seq_001", target_format="REEL", target_aspect_ratio="9:16",
        narrative_structure="HOOK -> CLOSING", shots=shots,
    )


def _register_asset(asset_id):
    return register_asset(
        _TEST_STORY_ID, asset_id=asset_id, scene_id="scene_02", type_="image", subtype="generated",
        filename=f"{asset_id}.jpeg", relative_path=f"images/generated/{asset_id}.jpeg",
        mime_type="image/jpeg", width=1024, height=1024, requested_aspect_ratio="9:16",
        source=None, provider="cloudflare", model="@cf/black-forest-labs/flux-1-schnell",
        prompt_version=1, parent_asset_id=None, references=[], provenance="AI_GENERATED", status="READY",
    )


def _run_animation_plan(story_id=_TEST_STORY_ID):
    return cli.cmd_animation_plan(argparse.Namespace(story_id=story_id))


def _capture_stdout(fn):
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn()
    return buf.getvalue()


def test_cmd_animation_plan_missing_sequence_returns_1(capsys):
    exit_code = _run_animation_plan()
    assert exit_code == 1
    out = json.loads(capsys.readouterr().out)
    assert "error" in out


def test_cmd_animation_plan_success_returns_0_and_prints_summary(capsys):
    _setup_sequence([
        _sequence_shot(shot_id="shot_01", scene_id="scene_01", order=1),
        _sequence_shot(
            shot_id="shot_02", scene_id="scene_02", order=2, asset_id="img_001",
            motion="SLOW_ZOOM_IN", transform_required=True, suggested_transform="EXTEND",
        ),
    ])
    _register_asset("img_001")

    exit_code = _run_animation_plan()
    assert exit_code == 0

    out = json.loads(capsys.readouterr().out)
    assert out["story_id"] == _TEST_STORY_ID
    assert out["sequence_id"] == "seq_001"
    assert out["total_shots"] == 2
    assert out["validation_errors"] == []
    assert out["status"] == "DRAFT"

    shot_02 = next(s for s in out["shots"] if s["shot_id"] == "shot_02")
    assert shot_02["asset_id"] == "img_001"
    assert shot_02["strategy"] == "DETERMINISTIC"
    assert shot_02["backend"] == "FFMPEG_LOCAL"
    assert shot_02["motion"] == "SLOW_ZOOM_IN"
    assert shot_02["source_transform"] == {"required": True, "suggested_transform": "EXTEND", "status": "PENDING"}

    shot_01 = next(s for s in out["shots"] if s["shot_id"] == "shot_01")
    assert shot_01["source_transform"] is None


def test_cmd_animation_plan_records_job():
    _setup_sequence([_sequence_shot()])
    out_job_id = json.loads(_capture_stdout(_run_animation_plan))["job_id"]

    from lab.core.paths import JOBS_DONE_DIR
    job_path = JOBS_DONE_DIR / f"{out_job_id}.json"
    assert job_path.exists()
    job = json.loads(job_path.read_text(encoding="utf-8"))
    assert job["type"] == "animation_plan"
    assert job["status"] == "done"
    assert job["params"]["story_id"] == _TEST_STORY_ID


def test_cmd_animation_plan_validation_errors_return_1_and_job_failed(capsys):
    _setup_sequence([_sequence_shot()])
    with patch("lab.animation.planner.validate_animation_plan", return_value=["error ficticio de prueba"]):
        exit_code = _run_animation_plan()
    assert exit_code == 1
    out = json.loads(capsys.readouterr().out)
    assert out["validation_errors"] == ["error ficticio de prueba"]


def test_cmd_animation_plan_does_not_modify_sequence_or_registry():
    _setup_sequence([_sequence_shot(asset_id="img_001", transform_required=True, suggested_transform="CROP")])
    _register_asset("img_001")

    seq_before = sequence_path(_TEST_STORY_ID).read_bytes()
    registry_before = asset_registry_path(_TEST_STORY_ID).read_bytes()

    _run_animation_plan()

    assert sequence_path(_TEST_STORY_ID).read_bytes() == seq_before
    assert asset_registry_path(_TEST_STORY_ID).read_bytes() == registry_before

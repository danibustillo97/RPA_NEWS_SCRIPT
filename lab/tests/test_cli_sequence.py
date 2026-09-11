"""
Tests de integracion de los comandos CLI `lab.cli sequence-record`,
`sequence-review` y `sequence-status` (Fase 4.1) -- los wrappers finos que
la skill lab-sequence-planning invoca. No vuelve a probar las reglas de
validacion (eso ya lo cubre test_sequence_planner.py contra
lab.sequence.planner directamente) -- solo que los comandos CLI conectan
esa capa correctamente: llaman al planner real, sequence-record registra
el job, sequence-review mueve el status, sequence-status lee y resume, y
ninguno de los tres toca media_blueprint.json/asset_registry.json.
"""

import argparse
import json
import shutil

import pytest

import lab.cli as cli
from lab.core.paths import JOBS_DONE_DIR, JOBS_FAILED_DIR
from lab.media.blueprint import init_blueprint
from lab.media.paths import asset_registry_path, media_blueprint_path, story_media_dir
from lab.media.registry import register_asset
from lab.sequence.planner import init_sequence, load

_TEST_STORY_ID = "_test_cli_sequence_story"


@pytest.fixture(autouse=True)
def _clean_test_story():
    # sequence-record es el unico de los tres que llama record_job() de
    # verdad -- sin este cleanup, cada corrida de tests dejaria archivos de
    # job reales acumulandose en lab/jobs/done|failed/.
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


def _setup_sequence(shots, target_aspect_ratio="9:16"):
    scene_ids = sorted({s["scene_id"] for s in shots})
    init_blueprint(
        _TEST_STORY_ID, visual_identity={"style_id": "test"}, characters=[], references=[],
        scenes=[{"scene_id": sid, "media_requirement": {"scene_id": sid}} for sid in scene_ids],
    )
    return init_sequence(
        _TEST_STORY_ID, sequence_id="seq_001", target_format="REEL", target_aspect_ratio=target_aspect_ratio,
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


def _run(cmd, story_id=_TEST_STORY_ID):
    return cmd(argparse.Namespace(story_id=story_id))


def _capture_stdout(fn):
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn()
    return buf.getvalue()


# --- sequence-record ----------------------------------------------------

def test_cmd_sequence_record_missing_sequence_returns_1(capsys):
    exit_code = _run(cli.cmd_sequence_record)
    assert exit_code == 1
    out = json.loads(capsys.readouterr().out)
    assert "error" in out


def test_cmd_sequence_record_success_returns_0_and_prints_summary(capsys):
    _setup_sequence([
        _sequence_shot(shot_id="shot_01", scene_id="scene_01", order=1),
        _sequence_shot(
            shot_id="shot_02", scene_id="scene_02", order=2, asset_id="img_001",
            motion="SLOW_ZOOM_IN", transform_required=True, suggested_transform="EXTEND",
        ),
    ])
    _register_asset("img_001")

    exit_code = _run(cli.cmd_sequence_record)
    assert exit_code == 0

    out = json.loads(capsys.readouterr().out)
    assert out["story_id"] == _TEST_STORY_ID
    assert out["sequence_id"] == "seq_001"
    assert out["total_shots"] == 2
    assert out["shots_with_asset"] == 1
    assert out["shots_text_only"] == 1
    assert out["shots_needing_transform"] == 1
    assert out["status"] == "DRAFT"


def test_cmd_sequence_record_records_job():
    _setup_sequence([_sequence_shot()])
    out_job_id = json.loads(_capture_stdout(lambda: _run(cli.cmd_sequence_record)))["job_id"]

    job_path = JOBS_DONE_DIR / f"{out_job_id}.json"
    assert job_path.exists()
    job = json.loads(job_path.read_text(encoding="utf-8"))
    assert job["type"] == "sequence_plan"
    assert job["status"] == "done"
    assert job["params"]["story_id"] == _TEST_STORY_ID


def test_cmd_sequence_record_validation_errors_return_1(capsys):
    # scene_01 no existe en media_blueprint.json -- invalido a proposito.
    init_blueprint(
        _TEST_STORY_ID, visual_identity={"style_id": "test"}, characters=[], references=[],
        scenes=[{"scene_id": "scene_other", "media_requirement": {"scene_id": "scene_other"}}],
    )
    init_sequence(
        _TEST_STORY_ID, sequence_id="seq_001", target_format="REEL", target_aspect_ratio="9:16",
        narrative_structure="HOOK -> CLOSING", shots=[_sequence_shot(scene_id="scene_01")],
    )

    exit_code = _run(cli.cmd_sequence_record)
    assert exit_code == 1
    out = json.loads(capsys.readouterr().out)
    assert out["error"] == "sequence.json inválido"
    assert out["details"]


def test_cmd_sequence_record_does_not_modify_blueprint_or_registry():
    _setup_sequence([_sequence_shot(asset_id="img_001", transform_required=True, suggested_transform="CROP")])
    _register_asset("img_001")

    blueprint_before = media_blueprint_path(_TEST_STORY_ID).read_bytes()
    registry_before = asset_registry_path(_TEST_STORY_ID).read_bytes()

    _run(cli.cmd_sequence_record)

    assert media_blueprint_path(_TEST_STORY_ID).read_bytes() == blueprint_before
    assert asset_registry_path(_TEST_STORY_ID).read_bytes() == registry_before


# --- sequence-review ------------------------------------------------------

def test_cmd_sequence_review_success_returns_0_and_updates_status(capsys):
    _setup_sequence([_sequence_shot()])

    exit_code = _run(cli.cmd_sequence_review)
    assert exit_code == 0

    out = json.loads(capsys.readouterr().out)
    assert out["story_id"] == _TEST_STORY_ID
    assert out["sequence_id"] == "seq_001"
    assert out["status"] == "READY_FOR_REVIEW"
    assert load(_TEST_STORY_ID)["status"] == "READY_FOR_REVIEW"


def test_cmd_sequence_review_validation_errors_return_1_and_status_unchanged(capsys):
    init_blueprint(
        _TEST_STORY_ID, visual_identity={"style_id": "test"}, characters=[], references=[],
        scenes=[{"scene_id": "scene_other", "media_requirement": {"scene_id": "scene_other"}}],
    )
    init_sequence(
        _TEST_STORY_ID, sequence_id="seq_001", target_format="REEL", target_aspect_ratio="9:16",
        narrative_structure="HOOK -> CLOSING", shots=[_sequence_shot(scene_id="scene_01")],
    )

    exit_code = _run(cli.cmd_sequence_review)
    assert exit_code == 1
    out = json.loads(capsys.readouterr().out)
    assert "no puede pasar a READY_FOR_REVIEW" in out["error"]
    assert load(_TEST_STORY_ID)["status"] == "DRAFT"


def test_cmd_sequence_review_missing_sequence_returns_1(capsys):
    exit_code = _run(cli.cmd_sequence_review)
    assert exit_code == 1
    out = json.loads(capsys.readouterr().out)
    assert "error" in out


# --- sequence-status --------------------------------------------------------

def test_cmd_sequence_status_missing_sequence_returns_1(capsys):
    exit_code = _run(cli.cmd_sequence_status)
    assert exit_code == 1
    out = json.loads(capsys.readouterr().out)
    assert "error" in out


def test_cmd_sequence_status_success_returns_0_and_prints_summary(capsys):
    _setup_sequence([
        _sequence_shot(shot_id="shot_01", scene_id="scene_01", order=1, duration_seconds=3.0),
        _sequence_shot(
            shot_id="shot_02", scene_id="scene_02", order=2, duration_seconds=4.5, asset_id="img_001",
            motion="SLOW_ZOOM_IN", transform_required=True, suggested_transform="EXTEND",
        ),
    ])
    _register_asset("img_001")

    exit_code = _run(cli.cmd_sequence_status)
    assert exit_code == 0

    out = json.loads(capsys.readouterr().out)
    assert out["story_id"] == _TEST_STORY_ID
    assert out["sequence_id"] == "seq_001"
    assert out["status"] == "DRAFT"
    assert out["target_format"] == "REEL"
    assert out["target_aspect_ratio"] == "9:16"
    assert out["total_shots"] == 2
    assert out["shots_with_asset"] == 1
    assert out["shots_text_only"] == 1
    assert out["shots_needing_transform"] == 1
    assert out["total_duration_seconds"] == 7.5


def test_cmd_sequence_status_does_not_record_job():
    _setup_sequence([_sequence_shot()])
    jobs_before = {p.name for p in JOBS_DONE_DIR.glob("*.json")} | {p.name for p in JOBS_FAILED_DIR.glob("*.json")}

    _run(cli.cmd_sequence_status)

    jobs_after = {p.name for p in JOBS_DONE_DIR.glob("*.json")} | {p.name for p in JOBS_FAILED_DIR.glob("*.json")}
    assert jobs_after == jobs_before

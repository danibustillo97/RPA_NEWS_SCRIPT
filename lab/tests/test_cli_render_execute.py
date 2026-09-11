"""
Tests de integracion del comando CLI `lab.cli render-execute` (Fase 4.2
etapa 5) -- el wrapper fino que corre create_and_run("render_execute", ...)
sobre lab.render.renderer.process_render_plan(). No vuelve a probar la
construccion del filtro FFmpeg ni la ejecucion real por shot (eso ya lo
cubre test_renderer.py, con FFmpeg real) -- solo que el comando CLI conecta
esa capa correctamente: un solo job por invocacion (no se ejecuta FFmpeg dos
veces), imprime el resumen esperado, y nunca toca
sequence.json/asset_registry.json/animation_plan.json.
"""

import argparse
import json
import shutil

import pytest

import lab.cli as cli
from lab.animation.paths import animation_plan_path
from lab.animation.planner import init_animation_plan
from lab.core.paths import JOBS_DONE_DIR, JOBS_FAILED_DIR
from lab.media.blueprint import init_blueprint
from lab.media.paths import asset_registry_path, sequence_path, story_media_dir
from lab.media.registry import register_asset
from lab.render.paths import rendered_video_path
from lab.render.planner import init_render_plan
from lab.sequence.planner import init_sequence

_TEST_STORY_ID = "_test_cli_render_execute_story"


@pytest.fixture(autouse=True)
def _clean_test_story():
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
        "order": 1, "duration_seconds": 1.0, "framing": "test",
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


def _register_real_asset(asset_id, width=64, height=64):
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


def _run_render_execute(story_id=_TEST_STORY_ID, shot_id=None):
    return cli.cmd_render_execute(argparse.Namespace(story_id=story_id, shot_id=shot_id))


def _capture_stdout(fn):
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn()
    return buf.getvalue()


def test_cmd_render_execute_missing_render_plan_returns_1(capsys):
    exit_code = _run_render_execute()
    assert exit_code == 1
    out = json.loads(capsys.readouterr().out)
    assert "error" in out


def test_cmd_render_execute_success_returns_0_and_prints_summary(capsys):
    _setup_animation_plan([
        _sequence_shot(shot_id="shot_01", scene_id="scene_01", order=1),
        _sequence_shot(
            shot_id="shot_02", scene_id="scene_02", order=2, asset_id="img_001",
            motion="SLOW_ZOOM_IN", transform_required=True, suggested_transform="EXTEND",
        ),
    ])
    _register_real_asset("img_001")
    init_render_plan(_TEST_STORY_ID)

    exit_code = _run_render_execute()
    assert exit_code == 0

    out = json.loads(capsys.readouterr().out)
    assert out["story_id"] == _TEST_STORY_ID
    assert out["processed"] == 2
    assert out["done"] == 1
    assert out["failed"] == 0
    assert out["pending"] == 1

    shot_02 = next(r for r in out["results"] if r["render_shot_id"] == "render_shot_02")
    assert shot_02["status"] == "DONE"
    assert shot_02["output_path"] == "videos/rendered/render_shot_02.mp4"
    assert rendered_video_path(_TEST_STORY_ID, "render_shot_02").exists()

    shot_01 = next(r for r in out["results"] if r["render_shot_id"] == "render_shot_01")
    assert shot_01["status"] == "PENDING"


def test_cmd_render_execute_runs_ffmpeg_exactly_once_per_shot(monkeypatch):
    """El comando CLI no debe volver a ejecutar process_render_plan() una vez
    por fuera del job -- solo el job (create_and_run) lo corre. Verifica que
    solo se produce UN archivo .mp4 (no se pisa/duplica la ejecución)."""
    _setup_animation_plan([
        _sequence_shot(shot_id="shot_01", scene_id="scene_01", order=1, asset_id="img_001",
                       transform_required=True, suggested_transform="EXTEND"),
    ])
    _register_real_asset("img_001")
    init_render_plan(_TEST_STORY_ID)

    call_count = {"n": 0}
    import lab.render.renderer as renderer_module
    original = renderer_module.process_render_plan

    def _counting_wrapper(*args, **kwargs):
        call_count["n"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(renderer_module, "process_render_plan", _counting_wrapper)

    _run_render_execute()

    assert call_count["n"] == 1


def test_cmd_render_execute_records_job():
    _setup_animation_plan([
        _sequence_shot(shot_id="shot_01", scene_id="scene_01", order=1, asset_id="img_001",
                       transform_required=True, suggested_transform="EXTEND"),
    ])
    _register_real_asset("img_001")
    init_render_plan(_TEST_STORY_ID)

    out_job_id = json.loads(_capture_stdout(_run_render_execute))["job_id"]

    job_path = JOBS_DONE_DIR / f"{out_job_id}.json"
    assert job_path.exists()
    job = json.loads(job_path.read_text(encoding="utf-8"))
    assert job["type"] == "render_execute"
    assert job["status"] == "done"
    assert job["params"]["story_id"] == _TEST_STORY_ID


def test_cmd_render_execute_shot_id_only_processes_that_shot(capsys):
    _setup_animation_plan([
        _sequence_shot(shot_id="shot_01", scene_id="scene_01", order=1, asset_id="img_001"),
        _sequence_shot(shot_id="shot_02", scene_id="scene_02", order=2, asset_id="img_002"),
    ])
    _register_real_asset("img_001")
    _register_real_asset("img_002")
    init_render_plan(_TEST_STORY_ID)

    exit_code = _run_render_execute(shot_id="render_shot_01")
    assert exit_code == 0

    out = json.loads(capsys.readouterr().out)
    assert out["processed"] == 1
    assert out["results"][0]["render_shot_id"] == "render_shot_01"
    assert not rendered_video_path(_TEST_STORY_ID, "render_shot_02").exists()


def test_cmd_render_execute_does_not_modify_animation_plan_sequence_or_registry():
    _setup_animation_plan([
        _sequence_shot(shot_id="shot_01", scene_id="scene_01", order=1, asset_id="img_001",
                       transform_required=True, suggested_transform="EXTEND"),
    ])
    _register_real_asset("img_001")
    init_render_plan(_TEST_STORY_ID)

    anim_plan_before = animation_plan_path(_TEST_STORY_ID).read_bytes()
    seq_before = sequence_path(_TEST_STORY_ID).read_bytes()
    registry_before = asset_registry_path(_TEST_STORY_ID).read_bytes()

    _run_render_execute()

    assert animation_plan_path(_TEST_STORY_ID).read_bytes() == anim_plan_before
    assert sequence_path(_TEST_STORY_ID).read_bytes() == seq_before
    assert asset_registry_path(_TEST_STORY_ID).read_bytes() == registry_before

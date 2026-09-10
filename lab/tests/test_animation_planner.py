"""
Tests de lab.animation.planner -- coherencia de referencias contra
sequence.json real, orden identico a Sequence, consistencia strategy<->backend,
manejo de transform_required/source_transform, motion declarativo, y que la
capa nunca crea assets ni escribe asset_registry.json/sequence.json.

Usa una historia descartable (story_id de prueba, limpiada en cada test) --
no toca datos reales de ninguna historia existente en el workspace.
"""

import json
import shutil

import pytest

from lab.animation.constants import ANIMATION_STRATEGIES, RENDER_BACKENDS
from lab.animation.paths import animation_plan_path
from lab.animation.planner import build_animation_shot, decide_strategy, init_animation_plan, load, set_status, validate_animation_plan
from lab.media.blueprint import init_blueprint
from lab.media.paths import asset_registry_path, sequence_path, story_media_dir
from lab.media.registry import register_asset
from lab.sequence.constants import MOTION_TYPES
from lab.sequence.planner import init_sequence

_TEST_STORY_ID = "_test_animation_story"


@pytest.fixture(autouse=True)
def _clean_test_story():
    shutil.rmtree(story_media_dir(_TEST_STORY_ID), ignore_errors=True)
    yield
    shutil.rmtree(story_media_dir(_TEST_STORY_ID), ignore_errors=True)


def _setup_blueprint(scene_ids):
    init_blueprint(
        _TEST_STORY_ID,
        visual_identity={"style_id": "test_style"},
        characters=[],
        references=[],
        scenes=[{"scene_id": sid, "media_requirement": {"scene_id": sid}} for sid in scene_ids],
    )


def _register_asset(asset_id, width=1024, height=1024):
    return register_asset(
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
        requested_aspect_ratio="9:16",
        source=None,
        provider="cloudflare",
        model="@cf/black-forest-labs/flux-1-schnell",
        prompt_version=1,
        parent_asset_id=None,
        references=[],
        provenance="AI_GENERATED",
        status="READY",
    )


def _sequence_shot(**overrides):
    shot = {
        "shot_id": "shot_01",
        "scene_id": "scene_01",
        "asset_id": None,
        "order": 1,
        "duration_seconds": 3.0,
        "framing": "test",
        "motion": "STATIC",
        "transition_in": "NONE",
        "transition_out": "CUT",
        "purpose": "hook",
        "notes": "",
        "transform_required": None,
        "suggested_transform": None,
    }
    shot.update(overrides)
    return shot


def _setup_sequence(shots):
    scene_ids = sorted({s["scene_id"] for s in shots})
    _setup_blueprint(scene_ids)
    return init_sequence(
        _TEST_STORY_ID,
        sequence_id="seq_001",
        target_format="REEL",
        target_aspect_ratio="9:16",
        narrative_structure="HOOK -> CLOSING",
        shots=shots,
    )


# --- decide_strategy / build_animation_shot ---------------------------------

def test_decide_strategy_covers_all_motion_types_as_deterministic():
    for motion in MOTION_TYPES:
        strategy, backend = decide_strategy(motion)
        assert strategy == "DETERMINISTIC"
        assert backend == "FFMPEG_LOCAL"


def test_decide_strategy_unknown_motion_raises():
    with pytest.raises(ValueError, match="motion desconocido"):
        decide_strategy("TELEPORT")


def test_build_animation_shot_text_only_has_null_source_transform():
    shot = build_animation_shot(_sequence_shot(asset_id=None, transform_required=None))
    assert shot["asset_id"] is None
    assert shot["source_transform"] is None
    assert shot["motion"] == {"type": "STATIC"}


def test_build_animation_shot_transform_required_produces_pending_source_transform():
    shot = build_animation_shot(_sequence_shot(
        asset_id="img_001", transform_required=True, suggested_transform="EXTEND",
    ))
    assert shot["source_transform"] == {"required": True, "suggested_transform": "EXTEND", "status": "PENDING"}


def test_build_animation_shot_transform_not_required_has_null_source_transform():
    shot = build_animation_shot(_sequence_shot(asset_id="img_001", transform_required=False))
    assert shot["source_transform"] is None


# --- init_animation_plan / set_status ----------------------------------------

def test_init_animation_plan_no_sequence_raises():
    with pytest.raises(ValueError, match="No hay sequence.json"):
        init_animation_plan(_TEST_STORY_ID)


def test_init_animation_plan_computes_total_duration_and_persists():
    _setup_sequence([
        _sequence_shot(shot_id="shot_01", scene_id="scene_01", order=1, duration_seconds=3.0),
        _sequence_shot(shot_id="shot_02", scene_id="scene_02", order=2, duration_seconds=4.0),
    ])
    plan = init_animation_plan(_TEST_STORY_ID)
    assert plan["total_duration_seconds"] == 7.0
    assert plan["sequence_id"] == "seq_001"
    assert plan["target_aspect_ratio"] == "9:16"
    assert plan["status"] == "DRAFT"
    assert len(plan["shots"]) == 2
    assert load(_TEST_STORY_ID)["animation_plan_id"] == "anim_001"


def test_set_status_no_plan_raises():
    with pytest.raises(ValueError, match="No hay animation_plan.json"):
        set_status(_TEST_STORY_ID, "READY_FOR_REVIEW")


def test_set_status_invalid_status_raises():
    _setup_sequence([_sequence_shot()])
    init_animation_plan(_TEST_STORY_ID)
    with pytest.raises(ValueError, match="status inválido"):
        set_status(_TEST_STORY_ID, "BOGUS")


# --- validate_animation_plan --------------------------------------------------

def test_validate_no_file_returns_error():
    errors = validate_animation_plan(_TEST_STORY_ID)
    assert len(errors) == 1
    assert "No hay animation_plan.json" in errors[0]


def test_validate_happy_path_no_errors():
    _setup_sequence([
        _sequence_shot(shot_id="shot_01", scene_id="scene_01", order=1),
        _sequence_shot(
            shot_id="shot_02", scene_id="scene_02", order=2, asset_id="img_001",
            motion="SLOW_ZOOM_IN", transform_required=True, suggested_transform="EXTEND",
        ),
    ])
    _register_asset("img_001")
    init_animation_plan(_TEST_STORY_ID)
    assert validate_animation_plan(_TEST_STORY_ID) == []


def test_validate_unknown_shot_id_errors():
    _setup_sequence([_sequence_shot()])
    init_animation_plan(_TEST_STORY_ID)
    plan = load(_TEST_STORY_ID)
    plan["shots"][0]["shot_id"] = "shot_99"
    animation_plan_path(_TEST_STORY_ID).write_text(json.dumps(plan), encoding="utf-8")
    errors = validate_animation_plan(_TEST_STORY_ID)
    assert any("shot_99" in e for e in errors)


def test_validate_divergent_scene_id_errors():
    _setup_sequence([_sequence_shot()])
    init_animation_plan(_TEST_STORY_ID)
    plan = load(_TEST_STORY_ID)
    plan["shots"][0]["scene_id"] = "scene_99"
    animation_plan_path(_TEST_STORY_ID).write_text(json.dumps(plan), encoding="utf-8")
    errors = validate_animation_plan(_TEST_STORY_ID)
    assert any("scene_id" in e for e in errors)


def test_validate_asset_id_not_in_registry_errors():
    _setup_sequence([_sequence_shot(asset_id="img_ghost", transform_required=True, suggested_transform="CROP")])
    init_animation_plan(_TEST_STORY_ID)
    errors = validate_animation_plan(_TEST_STORY_ID)
    assert any("img_ghost" in e for e in errors)


@pytest.mark.parametrize("strategy,backend,valid", [
    ("DETERMINISTIC", "FFMPEG_LOCAL", True),
    ("AI_VIDEO", "AI_VIDEO", True),
    ("AI_VIDEO", "FFMPEG_LOCAL", False),
    ("DETERMINISTIC", "AI_VIDEO", False),
])
def test_validate_strategy_backend_combinations(strategy, backend, valid):
    _setup_sequence([_sequence_shot()])
    init_animation_plan(_TEST_STORY_ID)
    plan = load(_TEST_STORY_ID)
    plan["shots"][0]["strategy"] = strategy
    plan["shots"][0]["backend"] = backend
    animation_plan_path(_TEST_STORY_ID).write_text(json.dumps(plan), encoding="utf-8")
    errors = validate_animation_plan(_TEST_STORY_ID)
    has_strategy_error = any("strategy/backend" in e for e in errors)
    assert has_strategy_error != valid


def test_validate_transform_required_false_but_source_transform_present_errors():
    _setup_sequence([_sequence_shot(asset_id="img_001", transform_required=False)])
    _register_asset("img_001")
    init_animation_plan(_TEST_STORY_ID)
    plan = load(_TEST_STORY_ID)
    plan["shots"][0]["source_transform"] = {"required": True, "suggested_transform": "CROP", "status": "PENDING"}
    animation_plan_path(_TEST_STORY_ID).write_text(json.dumps(plan), encoding="utf-8")
    errors = validate_animation_plan(_TEST_STORY_ID)
    assert any("transform_required no es true" in e for e in errors)


def test_validate_transform_required_true_but_source_transform_null_errors():
    _setup_sequence([_sequence_shot(asset_id="img_001", transform_required=True, suggested_transform="EXTEND")])
    _register_asset("img_001")
    init_animation_plan(_TEST_STORY_ID)
    plan = load(_TEST_STORY_ID)
    plan["shots"][0]["source_transform"] = None
    animation_plan_path(_TEST_STORY_ID).write_text(json.dumps(plan), encoding="utf-8")
    errors = validate_animation_plan(_TEST_STORY_ID)
    assert any("source_transform es null" in e for e in errors)


def test_validate_source_transform_status_must_be_pending():
    _setup_sequence([_sequence_shot(asset_id="img_001", transform_required=True, suggested_transform="EXTEND")])
    _register_asset("img_001")
    init_animation_plan(_TEST_STORY_ID)
    plan = load(_TEST_STORY_ID)
    plan["shots"][0]["source_transform"]["status"] = "APPLIED"
    animation_plan_path(_TEST_STORY_ID).write_text(json.dumps(plan), encoding="utf-8")
    errors = validate_animation_plan(_TEST_STORY_ID)
    assert any("PENDING" in e for e in errors)


def test_validate_no_asset_null_transform_is_valid():
    _setup_sequence([_sequence_shot(asset_id=None, transform_required=None)])
    init_animation_plan(_TEST_STORY_ID)
    assert validate_animation_plan(_TEST_STORY_ID) == []


def test_validate_invalid_motion_type_errors():
    _setup_sequence([_sequence_shot()])
    init_animation_plan(_TEST_STORY_ID)
    plan = load(_TEST_STORY_ID)
    plan["shots"][0]["motion"] = {"type": "TELEPORT"}
    animation_plan_path(_TEST_STORY_ID).write_text(json.dumps(plan), encoding="utf-8")
    errors = validate_animation_plan(_TEST_STORY_ID)
    assert any("motion.type" in e for e in errors)


def test_validate_non_positive_duration_errors():
    _setup_sequence([_sequence_shot()])
    init_animation_plan(_TEST_STORY_ID)
    plan = load(_TEST_STORY_ID)
    plan["shots"][0]["duration_seconds"] = 0
    animation_plan_path(_TEST_STORY_ID).write_text(json.dumps(plan), encoding="utf-8")
    errors = validate_animation_plan(_TEST_STORY_ID)
    assert any("duration_seconds" in e for e in errors)


def test_validate_order_mismatch_errors():
    _setup_sequence([
        _sequence_shot(shot_id="shot_01", scene_id="scene_01", order=1),
        _sequence_shot(shot_id="shot_02", scene_id="scene_02", order=2),
    ])
    init_animation_plan(_TEST_STORY_ID)
    plan = load(_TEST_STORY_ID)
    plan["shots"][0]["order"], plan["shots"][1]["order"] = 2, 1
    animation_plan_path(_TEST_STORY_ID).write_text(json.dumps(plan), encoding="utf-8")
    errors = validate_animation_plan(_TEST_STORY_ID)
    assert any("orden" in e for e in errors)


# --- aislamiento: no crea assets, no escribe registry ni sequence.json ------

def test_does_not_create_assets_or_touch_registry():
    _setup_sequence([_sequence_shot(asset_id="img_001", transform_required=True, suggested_transform="EXTEND")])
    _register_asset("img_001")

    registry_path = asset_registry_path(_TEST_STORY_ID)
    before = registry_path.read_bytes()

    init_animation_plan(_TEST_STORY_ID)

    after = registry_path.read_bytes()
    assert before == after


def test_does_not_modify_sequence_json():
    _setup_sequence([_sequence_shot()])
    seq_path = sequence_path(_TEST_STORY_ID)
    before = seq_path.read_bytes()

    init_animation_plan(_TEST_STORY_ID)

    after = seq_path.read_bytes()
    assert before == after


def test_animation_strategies_and_backends_vocab_unchanged():
    # cambios accidentales al vocabulario romperian silenciosamente las
    # combinaciones validas -- fijarlo explicitamente.
    assert ANIMATION_STRATEGIES == {"DETERMINISTIC", "AI_VIDEO"}
    assert RENDER_BACKENDS == {"FFMPEG_LOCAL", "AI_VIDEO"}

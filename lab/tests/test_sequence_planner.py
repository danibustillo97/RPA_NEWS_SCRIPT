"""
Tests de lab.sequence.planner -- derive_transform_requirement() (determinístico,
nunca decide el tipo de transformación) y validate_sequence() (referencias
reales a scene_id/asset_id, vocabulario, consistencia transform_required
<-> suggested_transform). Usa una historia descartable, no toca datos reales.
"""

import shutil

import pytest

from lab.media.blueprint import init_blueprint
from lab.media.paths import story_media_dir
from lab.media.registry import register_asset
from lab.sequence.planner import derive_transform_requirement, init_sequence, load, set_status, validate_sequence

_TEST_STORY_ID = "_test_sequence_story"


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


def _register_asset(asset_id, width, height):
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


def _valid_shot(**overrides):
    shot = {
        "shot_id": "shot_01",
        "scene_id": "scene_01",
        "asset_id": None,
        "order": 1,
        "duration_seconds": 3.0,
        "framing": "primer plano",
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


# --- derive_transform_requirement -------------------------------------------

def test_derive_transform_requirement_matches_returns_false():
    assert derive_transform_requirement("1:1", "1:1") is False


def test_derive_transform_requirement_differs_returns_true():
    assert derive_transform_requirement("1:1", "9:16") is True


def test_derive_transform_requirement_missing_actual_returns_true():
    # Caso real: img_001 (793ff158b714) es 1024x1024 -> actual_aspect_ratio "1:1",
    # target de una secuencia típica "9:16" -> difieren -> True.
    assert derive_transform_requirement(None, "9:16") is True


# --- init_sequence / set_status ---------------------------------------------

def test_init_sequence_computes_total_duration():
    _setup_blueprint(["scene_01", "scene_02"])
    sequence = init_sequence(
        _TEST_STORY_ID,
        sequence_id="seq_001",
        target_format="REEL",
        target_aspect_ratio="9:16",
        narrative_structure="HOOK -> CLOSING",
        shots=[
            _valid_shot(shot_id="shot_01", scene_id="scene_01", order=1, duration_seconds=3.0),
            _valid_shot(shot_id="shot_02", scene_id="scene_02", order=2, duration_seconds=4.5),
        ],
    )
    assert sequence["total_duration_seconds"] == 7.5
    assert sequence["status"] == "DRAFT"
    assert load(_TEST_STORY_ID)["sequence_id"] == "seq_001"


def test_set_status_no_sequence_raises():
    with pytest.raises(ValueError, match="No hay sequence.json"):
        set_status(_TEST_STORY_ID, "READY_FOR_REVIEW")


def test_set_status_invalid_status_raises():
    _setup_blueprint(["scene_01"])
    init_sequence(
        _TEST_STORY_ID, sequence_id="seq_001", target_format="REEL", target_aspect_ratio="9:16",
        narrative_structure="HOOK", shots=[_valid_shot()],
    )
    with pytest.raises(ValueError, match="status inválido"):
        set_status(_TEST_STORY_ID, "BOGUS")


# --- validate_sequence --------------------------------------------------------

def test_validate_sequence_no_file_returns_error():
    errors = validate_sequence(_TEST_STORY_ID)
    assert len(errors) == 1
    assert "No hay sequence.json" in errors[0]


def test_validate_sequence_valid_text_only_shot_no_errors():
    _setup_blueprint(["scene_01"])
    init_sequence(
        _TEST_STORY_ID, sequence_id="seq_001", target_format="REEL", target_aspect_ratio="9:16",
        narrative_structure="HOOK", shots=[_valid_shot()],
    )
    assert validate_sequence(_TEST_STORY_ID) == []


def test_validate_sequence_valid_shot_with_asset_and_transform_no_errors():
    _setup_blueprint(["scene_02"])
    _register_asset("img_001", width=1024, height=1024)
    shot = _valid_shot(
        shot_id="shot_02", scene_id="scene_02", asset_id="img_001",
        motion="SLOW_ZOOM_IN", transition_in="FADE",
        transform_required=True, suggested_transform="EXTEND",
    )
    init_sequence(
        _TEST_STORY_ID, sequence_id="seq_001", target_format="REEL", target_aspect_ratio="9:16",
        narrative_structure="HOOK", shots=[shot],
    )
    assert validate_sequence(_TEST_STORY_ID) == []


def test_validate_sequence_unknown_scene_id_errors():
    _setup_blueprint(["scene_01"])
    init_sequence(
        _TEST_STORY_ID, sequence_id="seq_001", target_format="REEL", target_aspect_ratio="9:16",
        narrative_structure="HOOK", shots=[_valid_shot(scene_id="scene_99")],
    )
    errors = validate_sequence(_TEST_STORY_ID)
    assert any("scene_id" in e and "scene_99" in e for e in errors)


def test_validate_sequence_unknown_asset_id_errors():
    _setup_blueprint(["scene_01"])
    shot = _valid_shot(asset_id="img_999", transform_required=True, suggested_transform="UNKNOWN")
    init_sequence(
        _TEST_STORY_ID, sequence_id="seq_001", target_format="REEL", target_aspect_ratio="9:16",
        narrative_structure="HOOK", shots=[shot],
    )
    errors = validate_sequence(_TEST_STORY_ID)
    assert any("asset_id" in e and "img_999" in e for e in errors)


def test_validate_sequence_invalid_motion_errors():
    _setup_blueprint(["scene_01"])
    init_sequence(
        _TEST_STORY_ID, sequence_id="seq_001", target_format="REEL", target_aspect_ratio="9:16",
        narrative_structure="HOOK", shots=[_valid_shot(motion="TELEPORT")],
    )
    errors = validate_sequence(_TEST_STORY_ID)
    assert any("motion" in e for e in errors)


def test_validate_sequence_invalid_transition_errors():
    _setup_blueprint(["scene_01"])
    init_sequence(
        _TEST_STORY_ID, sequence_id="seq_001", target_format="REEL", target_aspect_ratio="9:16",
        narrative_structure="HOOK", shots=[_valid_shot(transition_in="WHOOSH")],
    )
    errors = validate_sequence(_TEST_STORY_ID)
    assert any("transition_in" in e for e in errors)


def test_validate_sequence_transform_required_without_suggested_transform_errors():
    _setup_blueprint(["scene_01"])
    _register_asset("img_001", width=1024, height=1024)
    shot = _valid_shot(asset_id="img_001", transform_required=True, suggested_transform=None)
    init_sequence(
        _TEST_STORY_ID, sequence_id="seq_001", target_format="REEL", target_aspect_ratio="9:16",
        narrative_structure="HOOK", shots=[shot],
    )
    errors = validate_sequence(_TEST_STORY_ID)
    assert any("suggested_transform" in e for e in errors)


def test_validate_sequence_suggested_transform_without_transform_required_errors():
    _setup_blueprint(["scene_01"])
    _register_asset("img_001", width=1024, height=1024)
    shot = _valid_shot(asset_id="img_001", transform_required=False, suggested_transform="CROP")
    init_sequence(
        _TEST_STORY_ID, sequence_id="seq_001", target_format="REEL", target_aspect_ratio="9:16",
        narrative_structure="HOOK", shots=[shot],
    )
    errors = validate_sequence(_TEST_STORY_ID)
    assert any("suggested_transform" in e for e in errors)


def test_validate_sequence_null_asset_with_nonnull_transform_fields_errors():
    _setup_blueprint(["scene_01"])
    shot = _valid_shot(asset_id=None, transform_required=True, suggested_transform="CROP")
    init_sequence(
        _TEST_STORY_ID, sequence_id="seq_001", target_format="REEL", target_aspect_ratio="9:16",
        narrative_structure="HOOK", shots=[shot],
    )
    errors = validate_sequence(_TEST_STORY_ID)
    assert any("deben ser null" in e for e in errors)


def test_validate_sequence_duplicate_order_errors():
    _setup_blueprint(["scene_01", "scene_02"])
    shots = [
        _valid_shot(shot_id="shot_01", scene_id="scene_01", order=1),
        _valid_shot(shot_id="shot_02", scene_id="scene_02", order=1),
    ]
    init_sequence(
        _TEST_STORY_ID, sequence_id="seq_001", target_format="REEL", target_aspect_ratio="9:16",
        narrative_structure="HOOK", shots=shots,
    )
    errors = validate_sequence(_TEST_STORY_ID)
    assert any("order" in e for e in errors)


def test_validate_sequence_empty_shots_errors():
    _setup_blueprint(["scene_01"])
    init_sequence(
        _TEST_STORY_ID, sequence_id="seq_001", target_format="REEL", target_aspect_ratio="9:16",
        narrative_structure="HOOK", shots=[],
    )
    errors = validate_sequence(_TEST_STORY_ID)
    assert any("ningún shot" in e for e in errors)

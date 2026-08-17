import pytest

from ddda_miro.coordinates import frame_center_to_parent_position


def test_frame_center_coordinates_are_converted_to_miro_parent_top_left():
    result = frame_center_to_parent_position(
        {"x": -1200, "y": 450, "origin": "center"},
        {"width": 5000, "height": 3200},
        child_geometry={"width": 1100},
        label="project-charter",
    )

    assert result == {"x": 1300.0, "y": 2050.0, "origin": "center"}


def test_child_outside_parent_is_rejected_before_miro_api_call():
    with pytest.raises(ValueError, match="exceeds parent width"):
        frame_center_to_parent_position(
            {"x": -2400, "y": 0},
            {"width": 5000, "height": 3200},
            child_geometry={"width": 1000},
            label="invalid-child",
        )


def test_parent_geometry_is_required_for_attached_item():
    with pytest.raises(ValueError, match="requires width and height"):
        frame_center_to_parent_position({"x": 0, "y": 0}, {}, label="missing-frame")

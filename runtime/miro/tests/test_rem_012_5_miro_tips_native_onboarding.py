from ddda_miro import miro_tips_native_onboarding as onboarding


def manifest():
    return {
        "miro_tips": {
            "onboarding": {
                "mode": onboarding.MODE,
                "policy": onboarding.POLICY,
                "minimum_body_font_size": 36,
                "minimum_heading_font_size": 64,
                "minimum_sections": 6,
                "required_sections": list(onboarding.REQUIRED_SECTIONS),
                "container_geometry": {"width": 1919.4331503618523, "height": 1079.6811470785374},
                "container_position": {"x": -19834.447049390445, "y": -11727.529671450406},
            }
        }
    }


def test_native_onboarding_contract_requires_readable_six_section_surface():
    value = manifest()
    assert onboarding.config(value)["minimum_body_font_size"] == 36
    assert len(onboarding.desired_items("tips", value)) == 7
    value["miro_tips"]["onboarding"]["minimum_body_font_size"] = 35
    try:
        onboarding.config(value)
    except ValueError as exc:
        assert "36px body" in str(exc)
    else:
        raise AssertionError("expected readability contract rejection")


def test_native_onboarding_has_no_screenshot_or_callout_content():
    items = onboarding.desired_items("tips", manifest())
    joined = " ".join(item["data"]["content"] for item in items)
    assert "screenshot" not in joined.lower()
    assert "transparent" not in joined.lower()
    assert items[0]["style"]["fontSize"] == "64"
    assert all(item["style"]["fontSize"] == "36" for item in items[1:])


def test_native_onboarding_children_stay_inside_the_retained_frame():
    items = onboarding.desired_items("tips", manifest())
    width, height = 1919.4331503618523, 1079.6811470785374
    for item in items:
        position, geometry = item["position"], item["geometry"]
        assert abs(position["x"]) + geometry["width"] / 2 <= width / 2
        assert abs(position["y"]) + geometry["height"] / 2 <= height / 2

from __future__ import annotations

import json
from pathlib import Path

from ruamel.yaml import YAML


ROOT = Path(__file__).resolve().parents[3]


def _load_profiles() -> dict:
    return YAML(typ="safe").load(
        (ROOT / "config/platform/miro-execution-profiles.yaml").read_text(encoding="utf-8")
    )


def test_miro_execution_profiles_are_explicit_and_rest_first():
    cfg = _load_profiles()
    assert cfg["contract"] == "ddda-miro-execution-profiles"
    assert cfg["principles"]["deterministic_transport"] == "rest-api"
    assert cfg["principles"]["mcp_required_for_technical_gate"] is False
    assert cfg["principles"]["active_development_profiles"] == [
        "platform_lab",
        "github_ci",
        "hvr",
    ]
    assert cfg["principles"]["deferred_profiles"] == [
        "example_project",
        "project_runtime",
    ]

    profiles = cfg["profiles"]
    assert set(profiles) == {
        "platform_lab",
        "github_ci",
        "hvr",
        "mcp",
        "example_project",
        "project_runtime",
    }
    for name in ("platform_lab", "github_ci", "hvr"):
        assert profiles[name]["enabled"] is True
        assert profiles[name]["transport"] == "rest-api"
    assert profiles["mcp"]["transport"] == "mcp"
    assert profiles["mcp"]["technical_gate_required"] is False
    assert profiles["example_project"]["enabled"] is False
    assert profiles["project_runtime"]["enabled"] is False


def test_active_development_profiles_use_three_independent_credentials_and_boards():
    cfg = _load_profiles()
    profiles = cfg["profiles"]

    expected = {
        "platform_lab": (
            "MIRO_PLATFORM_LAB_ACCESS_TOKEN",
            "DDDA_MIRO_PLATFORM_LAB_BOARD_ID",
            "DDDA_PLATFORM_LAB",
            "uXjVH0doLYY=",
        ),
        "github_ci": (
            "MIRO_GH_CI_ACCESS_TOKEN",
            "DDDA_MIRO_GH_CI_BOARD_ID",
            "DDDA_GH_CI",
            "uXjVHy7iQD4=",
        ),
        "hvr": (
            "MIRO_HVR_ACCESS_TOKEN",
            "DDDA_MIRO_HVR_BOARD_ID",
            "DDDA_HVR",
            None,
        ),
    }
    for name, (secret, board_env, board_name, fallback_id) in expected.items():
        profile = profiles[name]
        assert profile["access_token_secret"] == secret
        assert profile["board_id_env"] == board_env
        assert profile["board_name"] == board_name
        if fallback_id is not None:
            assert profile["current_board_id_fallback"] == fallback_id

    assert profiles["github_ci"]["reset_policy"] == "clear-all-items-before-run"
    assert profiles["github_ci"]["ownership"] == "machine-only"
    assert profiles["hvr"]["source_profile"] == "platform_lab"
    assert profiles["hvr"]["materialization"] == "replace-by-server-side-board-copy"

    text = json.dumps(cfg)
    assert "MIRO_CI_ACCESS_TOKEN" not in text
    assert '"MIRO_ACCESS_TOKEN"' not in text
    assert "legacy_access_token_secret" not in text
    assert "fallback_access_token_secrets" not in text


def test_profile_contract_contains_only_secret_names_not_token_values():
    cfg = _load_profiles()
    text = json.dumps(cfg)
    assert "Bearer " not in text
    assert "access_token:" not in text
    for profile in cfg["profiles"].values():
        for key, value in profile.items():
            if key == "access_token_secret" and isinstance(value, str):
                assert value.startswith("MIRO_") and value.endswith("ACCESS_TOKEN")


def test_development_policy_requires_three_profile_contract_and_mcp_is_optional():
    policy = json.loads(
        (ROOT / "config/platform/development-policy.yaml").read_text(encoding="utf-8")
    )
    remote = policy["remote_execution"]
    assert remote["miro_execution_profile_config"] == "config/platform/miro-execution-profiles.yaml"
    assert remote["deterministic_miro_transport"] == "rest-api"
    assert remote["mcp_required_for_technical_gate"] is False
    assert remote["active_miro_profiles"] == ["platform_lab", "github_ci", "hvr"]
    assert remote["required_miro_secret_names"] == [
        "MIRO_PLATFORM_LAB_ACCESS_TOKEN",
        "MIRO_GH_CI_ACCESS_TOKEN",
        "MIRO_HVR_ACCESS_TOKEN",
    ]
    assert remote["legacy_secret_fallback_allowed_for_pr8"] is False
    assert remote["deferred_miro_profiles"] == ["example_project", "project_runtime"]

    project_runtime = policy["execution_interfaces"]["ddda_project_runtime"]
    assert project_runtime["current_activation_status"] == "deferred"
    project_miro = project_runtime["miro"]
    assert project_miro["token_indirection_required"] is True
    assert project_miro["team_independently_configurable"] is True
    assert project_miro["space_independently_configurable"] is True
    assert project_miro["create_board_if_missing_supported"] is True


def test_project_manifest_contract_still_supports_future_per_project_miro_binding():
    schema = json.loads((ROOT / "schemas/project.schema.json").read_text(encoding="utf-8"))
    fields = schema["properties"]["miro"]["properties"]
    for field in (
        "board_id",
        "board_id_env",
        "access_token_env",
        "team_id",
        "team_id_env",
        "project_id",
        "project_id_env",
    ):
        assert field in fields

    template = (ROOT / "templates/project/project.yaml").read_text(encoding="utf-8")
    assert "access_token_env:" in template
    assert "team_id_env:" in template
    assert "project_id_env:" in template
    assert "board_id_env:" in template


def test_pr8_workflows_use_strict_profile_credentials_and_not_mcp_transport():
    platform = (ROOT / ".github/workflows/platform-ci.yml").read_text(encoding="utf-8")
    hvr = (ROOT / ".github/workflows/miro-frame01-redline.yml").read_text(encoding="utf-8")

    for marker in (
        "Miro profile bindings",
        "Materialize DDDA_HVR from validated Platform Lab",
        "hvr-materialization-",
        "MIRO_PLATFORM_LAB_ACCESS_TOKEN",
        "MIRO_GH_CI_ACCESS_TOKEN",
        "MIRO_HVR_ACCESS_TOKEN",
        "DDDA_MIRO_GH_CI_BOARD_ID",
        "ACCEPTANCE_CLAIMS_MODERNIZATION_MIRO_BOARD_ID",
        "Reset dedicated DDDA_GH_CI board",
    ):
        assert marker in platform
    assert "secrets.MIRO_ACCESS_TOKEN" not in platform
    assert "MIRO_CI_ACCESS_TOKEN" not in platform

    for marker in (
        "workflow_dispatch:",
        "verify_reference_composite",
        "reference_composite_image",
        "platform_lab_write_authorized=$false",
        "hvr_write_authorized=$false",
    ):
        assert marker in hvr
    assert "pull_request:" not in hvr
    assert "push:" not in hvr
    assert "MIRO_PLATFORM_LAB_ACCESS_TOKEN" not in hvr
    assert "MIRO_HVR_ACCESS_TOKEN" not in hvr
    assert "--apply" not in hvr
    assert "|| secrets." not in hvr
    assert "secrets.MIRO_ACCESS_TOKEN" not in hvr
    assert "mcp_server" not in hvr.casefold()
    assert "api_tool" not in hvr


def test_standard_platform_ci_materializes_hvr_only_after_online_acceptance():
    platform = (ROOT / ".github/workflows/platform-ci.yml").read_text(encoding="utf-8")
    assert "materialize-hvr:" in platform
    assert "- online-miro-acceptance" in platform
    assert "Require completed exact-SHA technical checks" in platform
    assert "Exact-code Miro image probe" in platform
    assert "miro-runtime-tests" in platform
    assert "Reconcile and read back DDDA_PLATFORM_LAB" in platform
    assert "Replace DDDA_HVR by server-side copy and read back" in platform
    assert "MIRO_PLATFORM_LAB_ACCESS_TOKEN" in platform
    assert "MIRO_HVR_ACCESS_TOKEN" in platform
    assert "hvr_materialization" in platform
    assert "MIRO_ACCESS_TOKEN: ${{ secrets.MIRO_HVR_ACCESS_TOKEN }}" not in platform


def test_standard_hvr_gate_enforces_exact_reference_clone_and_rejects_retired_composite_contract():
    platform = (ROOT / ".github/workflows/platform-ci.yml").read_text(encoding="utf-8")

    for marker in (
        "exact_reference_clone",
        "exact_reference_child_snapshot",
        "reference_clone.status",
        "reference_clone.target_item_count -ne 17",
        "reference_clone.target_connector_count -ne 8",
        "reference_clone.native_item_count -ne 16",
        "3458764679531043366",
        "3458764679531043367",
        "04b83ec7d9bc07ae31c7c11c03ec974ff4bde00d7773d7f9e55036e877f6fffd",
        "miro_tips.review_url",
    ):
        assert marker in platform

    for retired in (
        "reference_composite_image",
        "bit_exact_composite_asset",
        "c436088d322d600c748ed99079001965e87c1b267397c096738bb8a7ab077a55",
        ".miro_tips.composite_sha256",
        ".miro_tips.rendered_sha256",
    ):
        assert retired not in platform

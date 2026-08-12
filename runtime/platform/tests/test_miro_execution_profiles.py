from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]


def _load_profiles() -> dict:
    return yaml.safe_load(
        (ROOT / "config/platform/miro-execution-profiles.yaml").read_text(encoding="utf-8")
    )


def test_miro_execution_profiles_are_explicit_and_rest_first():
    cfg = _load_profiles()
    assert cfg["contract"] == "ddda-miro-execution-profiles"
    assert cfg["principles"]["deterministic_transport"] == "rest-api"
    assert cfg["principles"]["mcp_required_for_technical_gate"] is False

    profiles = cfg["profiles"]
    assert set(profiles) == {
        "platform_lab",
        "example_project",
        "github_ci",
        "hvr",
        "mcp",
        "project_runtime",
    }
    for name in ("platform_lab", "example_project", "github_ci", "hvr", "project_runtime"):
        assert profiles[name]["transport"] == "rest-api"
    assert profiles["mcp"]["transport"] == "mcp"
    assert profiles["mcp"]["technical_gate_required"] is False


def test_profile_contract_contains_only_secret_names_not_token_values():
    cfg = _load_profiles()
    text = json.dumps(cfg)
    assert "Bearer " not in text
    assert "access_token:" not in text
    for profile in cfg["profiles"].values():
        for key, value in profile.items():
            if "access_token_secret" in key and isinstance(value, str):
                assert value.startswith("MIRO_") and value.endswith("ACCESS_TOKEN")


def test_development_policy_requires_profile_contract_and_mcp_is_optional():
    policy = json.loads(
        (ROOT / "config/platform/development-policy.yaml").read_text(encoding="utf-8")
    )
    remote = policy["remote_execution"]
    assert remote["miro_execution_profile_config"] == "config/platform/miro-execution-profiles.yaml"
    assert remote["deterministic_miro_transport"] == "rest-api"
    assert remote["mcp_required_for_technical_gate"] is False
    project_miro = policy["execution_interfaces"]["ddda_project_runtime"]["miro"]
    assert project_miro["token_indirection_required"] is True
    assert project_miro["team_independently_configurable"] is True
    assert project_miro["space_independently_configurable"] is True
    assert project_miro["create_board_if_missing_supported"] is True


def test_project_manifest_contract_already_supports_per_project_miro_binding():
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


def test_pr8_hvr_uses_rest_secret_chain_and_not_mcp():
    workflow = (ROOT / ".github/workflows/miro-frame01-redline.yml").read_text(encoding="utf-8")
    assert "MIRO_HVR_ACCESS_TOKEN" in workflow
    assert "MIRO_PLATFORM_LAB_ACCESS_TOKEN" in workflow
    assert "DDDA_MIRO_PLATFORM_LAB_BOARD_ID" in workflow
    assert "python -m ddda_miro.connector_readback_wirefix" in workflow
    assert "MCP" not in workflow

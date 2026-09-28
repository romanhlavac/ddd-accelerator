from copy import deepcopy
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[3]
SCHEMA = json.loads((ROOT / "schemas/candidate-context.schema.json").read_text(encoding="utf-8"))


def context() -> dict:
    source_sha = "a" * 40
    package_sha = "b" * 64
    return {
        "schema_version": 1,
        "context_kind": "ddda_candidate_context",
        "candidate_kind": "NORMAL",
        "release_mode": "STANDARD",
        "operation": "merge_dry_run",
        "repository": "romanhlavac/ddd-accelerator",
        "pr": 176,
        "base_branch": "main",
        "source_branch": "test/174-governance-characterization",
        "source_sha": source_sha,
        "version": "0.1.2",
        "generation": 1,
        "pr_state": "READY",
        "validation_evidence": {
            "status": "PASS",
            "source_sha": source_sha,
            "package_sha256": package_sha,
            "artifact_name": f"ddda-candidate-{source_sha}",
            "workflow_run_id": 36355784058,
        },
        "authoritative_check_summary": {
            "status": "PASS",
            "required_checks": ["Platform validation"],
            "latest_results": [
                {
                    "name": "Platform validation",
                    "status": "COMPLETED",
                    "conclusion": "SUCCESS",
                    "run_id": 36355784058,
                }
            ],
        },
        "human_review_reference": {
            "verdict": "PASS",
            "reviewed_sha": source_sha,
            "candidate_package_sha256": package_sha,
            "reviewer": "romanhlavac",
            "reviewed_at": "2026-09-28T07:54:55Z",
            "provenance_verified": True,
        },
        "hrdr_reference": None,
        "physical_scope_reference": None,
        "project_evidence_reference": None,
    }


def test_candidate_context_v1_schema_accepts_exact_identity():
    jsonschema.validate(context(), SCHEMA, format_checker=jsonschema.FormatChecker())


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("source_sha",), "not-a-sha"),
        (("validation_evidence", "package_sha256"), "wrong"),
        (("operation",), "promote"),
        (("pr",), 0),
    ],
)
def test_candidate_context_v1_schema_rejects_invalid_contract_values(path, value):
    candidate = deepcopy(context())
    target = candidate
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(candidate, SCHEMA, format_checker=jsonschema.FormatChecker())


def test_candidate_context_v1_schema_rejects_unversioned_extension():
    candidate = context()
    candidate["implicit_authorization"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(candidate, SCHEMA)

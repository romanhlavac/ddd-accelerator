import json
from pathlib import Path

from runtime.platform.mismatch_taxonomy import classify_mismatch, classify_result

ROOT = Path(__file__).resolve().parents[3]


def test_taxonomy_is_versioned_and_every_code_gets_one_primary_category():
    taxonomy = json.loads((ROOT / "config/governance/mismatch-taxonomy-v1.json").read_text())
    schema = json.loads((ROOT / "schemas/governance-mismatch-taxonomy.schema.json").read_text())
    assert taxonomy["schema_version"] == schema["properties"]["schema_version"]["const"]
    assert set(taxonomy["categories"]) == set(schema["properties"]["categories"]["required"])

    assert classify_mismatch("MILESTONE_SCOPE_MISMATCH")["primary_category"] == "SAFETY_BLOCKING"
    assert classify_mismatch("DELIVERY_STATUS_MISMATCH")["primary_category"] == "GOVERNANCE_PROJECTION"
    assert classify_mismatch("PRESENTATION_WP_MISMATCH")["primary_category"] == "PRESENTATION"
    assert classify_mismatch("UNRECOGNIZED_DRIFT")["primary_category"] == "SAFETY_BLOCKING"
    assert len(classify_result("PROJECT_TITLE_MISMATCH+PRESENTATION_WP_MISMATCH")) == 2


def test_project_mutation_audit_keeps_zero_mismatch_transaction_gate():
    workflow = (ROOT / ".github/workflows/reconcile-ddda-project-backlog.yml").read_text()
    assert "assert audit['remaining_count'] == 0" in workflow
    assert "assert presentation['remaining_count'] == 0" in workflow

import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[3]
SCHEMA = json.loads(
    (ROOT / "schemas/release-source-recovery-ledger.schema.json").read_text(encoding="utf-8")
)


def ledger(version: int) -> dict:
    value = {
        "schema_version": version,
        "version": "0.1.1",
        "previous_release_tag": "v0.1.0",
        "entries": [{
            "recovered_commit_sha": "a" * 40,
            "source_pr": 97,
            "source_merge_commit_sha": "b" * 40,
            "primary_cr": 96,
        }],
    }
    if version == 2:
        value["release_cut"] = {
            "commit_sha": "c" * 40,
            "path": "CHANGELOG.md",
            "source_blob_sha": "d" * 40,
            "release_blob_sha": "e" * 40,
            "version": "0.1.1",
        }
    return value


def test_schema_keeps_v1_readable_and_requires_release_cut_only_for_v2():
    jsonschema.validate(ledger(1), SCHEMA)
    jsonschema.validate(ledger(2), SCHEMA)

    invalid_v2 = ledger(2)
    del invalid_v2["release_cut"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(invalid_v2, SCHEMA)

    invalid_v1 = ledger(1)
    invalid_v1["release_cut"] = ledger(2)["release_cut"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(invalid_v1, SCHEMA)


def test_schema_rejects_release_cut_path_or_blob_ambiguity():
    invalid = ledger(2)
    invalid["release_cut"]["path"] = "docs/notes.md"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(invalid, SCHEMA)

    invalid = ledger(2)
    invalid["release_cut"]["source_blob_sha"] = "not-a-sha"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(invalid, SCHEMA)

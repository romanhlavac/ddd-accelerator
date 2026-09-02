from runtime.platform.release_governance import evaluate_recovery_ledger


def test_recovery_ledger_accepts_collector_derived_metadata_commit():
    recovered = "d" * 40
    metadata = "e" * 40
    physical = {
        "previous_release_tag": "v0.1.0",
        "commit_shas": [recovered, metadata],
        "recovery_ledger": {
            "schema_version": 1,
            "version": "0.1.1",
            "previous_release_tag": "v0.1.0",
            "metadata_commit_shas": [metadata],
            "entries": [
                {
                    "recovered_commit_sha": recovered,
                    "source_pr": 97,
                    "primary_cr": 96,
                    "source_pr_merged": True,
                    "source_primary_crs": [96],
                    "source_merge_commit_sha": "f" * 40,
                    "observed_source_merge_commit_sha": "f" * 40,
                    "changed_path_hashes_match": True,
                }
            ],
        },
    }

    assert evaluate_recovery_ledger(
        physical,
        expected_version="0.1.1",
        declared_scope={96},
    ) == []

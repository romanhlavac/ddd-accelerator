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


def test_recovery_ledger_v2_accepts_exact_one_file_release_cut_and_ledger_tip():
    recovered = "d" * 40
    release_cut = "e" * 40
    ledger_tip = "f" * 40
    physical = {
        "previous_release_tag": "v0.1.0",
        "commit_shas": [recovered, release_cut, ledger_tip],
        "recovery_ledger": {
            "schema_version": 2,
            "version": "0.1.1",
            "previous_release_tag": "v0.1.0",
            "metadata_commit_shas": [release_cut, ledger_tip],
            "release_cut": {
                "commit_sha": release_cut,
                "path": "CHANGELOG.md",
                "version": "0.1.1",
                "source_blob_sha": "1" * 40,
                "release_blob_sha": "2" * 40,
                "changed_paths_match": True,
                "source_blob_matches": True,
                "release_blob_matches": True,
            },
            "entries": [
                {
                    "recovered_commit_sha": recovered,
                    "source_pr": 97,
                    "primary_cr": 96,
                    "source_pr_merged": True,
                    "source_primary_crs": [96],
                    "source_merge_commit_sha": "a" * 40,
                    "observed_source_merge_commit_sha": "a" * 40,
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


def test_recovery_ledger_v2_rejects_release_cut_blob_or_path_drift():
    release_cut = "e" * 40
    physical = {
        "previous_release_tag": "v0.1.0",
        "commit_shas": ["d" * 40, release_cut, "f" * 40],
        "recovery_ledger": {
            "schema_version": 2,
            "version": "0.1.1",
            "previous_release_tag": "v0.1.0",
            "metadata_commit_shas": [release_cut, "f" * 40],
            "release_cut": {
                "commit_sha": release_cut,
                "path": "CHANGELOG.md",
                "version": "0.1.1",
                "changed_paths_match": False,
                "source_blob_matches": True,
                "release_blob_matches": False,
            },
            "entries": [{
                "recovered_commit_sha": "d" * 40,
                "source_pr": 97,
                "primary_cr": 96,
                "source_pr_merged": True,
                "source_primary_crs": [96],
                "source_merge_commit_sha": "a" * 40,
                "observed_source_merge_commit_sha": "a" * 40,
                "changed_path_hashes_match": True,
            }],
        },
    }

    failures = evaluate_recovery_ledger(
        physical,
        expected_version="0.1.1",
        declared_scope={96},
    )
    assert "RECOVERY_LEDGER_RELEASE_CUT_PATHS_MISMATCH" in failures
    assert "RECOVERY_LEDGER_RELEASE_CUT_RESULT_BLOB_MISMATCH" in failures


def test_recovery_ledger_v2_rejects_release_cut_that_is_not_penultimate():
    recovered = "d" * 40
    release_cut = "e" * 40
    ledger_tip = "f" * 40
    physical = {
        "previous_release_tag": "v0.1.0",
        "commit_shas": [release_cut, recovered, ledger_tip],
        "recovery_ledger": {
            "schema_version": 2,
            "version": "0.1.1",
            "previous_release_tag": "v0.1.0",
            "metadata_commit_shas": [release_cut, ledger_tip],
            "release_cut": {
                "commit_sha": release_cut,
                "path": "CHANGELOG.md",
                "version": "0.1.1",
                "changed_paths_match": True,
                "source_blob_matches": True,
                "release_blob_matches": True,
            },
            "entries": [{
                "recovered_commit_sha": recovered,
                "source_pr": 97,
                "primary_cr": 96,
                "source_pr_merged": True,
                "source_primary_crs": [96],
                "source_merge_commit_sha": "a" * 40,
                "observed_source_merge_commit_sha": "a" * 40,
                "changed_path_hashes_match": True,
            }],
        },
    }

    failures = evaluate_recovery_ledger(
        physical,
        expected_version="0.1.1",
        declared_scope={96},
    )
    assert "RECOVERY_LEDGER_RELEASE_CUT_SEQUENCE_INVALID" in failures

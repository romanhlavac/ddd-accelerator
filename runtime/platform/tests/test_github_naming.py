import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "github_naming",
    Path(__file__).resolve().parents[3] / "scripts/platform/Audit-DDDAGitHubNaming.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def issue(number, title, body="", labels=(), state="open", pr=False):
    row = {"number": number, "title": title, "body": body, "state": state,
           "labels": [{"name": x} for x in labels]}
    if pr:
        row["pull_request"] = {"url": "https://api.github.com/pulls/1"}
    return row


def test_additive_plan_and_zero_write_second_run():
    row = issue(132, "[CR][GOV][DOC] Name", "Platform Areas: DOC, TESTING")
    first = module.plan([row], [], [], [], [])
    assert first["write_count"] == 1
    assert first["writes"] == [{"number": 132, "add_labels": ["documentation"]}]
    row["labels"].append({"name": "documentation"})
    second = module.plan([row], [], [], [], [])
    assert second["write_count"] == 0
    assert second["plan_sha256"] != first["plan_sha256"]


def test_ambiguous_alias_and_unstructured_evidence_never_write():
    rows = [
        issue(2, "[CHR] Old", "Platform Areas: DOC"),
        issue(3, "Interesting DOC idea", "documentation mentioned in prose"),
        issue(4, "[CR] Conflicting", "Platform Areas: DOC\nPlatform Areas: TESTING"),
    ]
    result = module.plan(rows, [], [], [], [])
    assert result["write_count"] == 0
    assert result["records"][0]["classification"] == "AMBIGUOUS"


def test_closed_pr_ref_tag_release_preserved():
    result = module.plan(
        [issue(8, "[0.1.0][#17] historical", "Platform Areas: DOC",
               state="closed", pr=True)],
        [{"name": "gov/old"}], [{"name": "v0.1.0"}],
        [{"tag_name": "v0.1.1", "name": "DDDA 0.1.1"}],
        [{"name": "DDDA platform CI", "path": ".github/workflows/platform-ci.yml"}],
    )
    assert result["write_count"] == 0
    assert all(x["classification"] == "PRESERVE_AS_HISTORICAL_IDENTITY"
               for x in result["records"])


def test_candidate_title_does_not_grant_identity():
    result = module.classify_issue(
        issue(103, "[RELEASE][0.1.1] Release candidate", state="open", pr=True)
    )
    assert result["classification"] == "AMBIGUOUS"
    assert result["add_labels"] == []

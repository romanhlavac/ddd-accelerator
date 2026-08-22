import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/platform/Reconcile-DDDAProjectBacklogPresentation.py"
WORKFLOW = ROOT / ".github/workflows/reconcile-ddda-project-backlog.yml"


def _ns():
    return runpy.run_path(str(SCRIPT))


def test_authority_reflects_scope_strangler_work_package_moves():
    authority = _ns()["load_authority"]()
    assert authority[36] == "WP-13"
    assert authority[41] == "WP-13"
    assert authority[45] == "Other"
    assert authority[53] == "WP-12"
    assert authority[57] == "WP-12"
    assert authority[60] == "WP-12"
    assert authority[61] == "WP-13"


def test_explicit_stale_wp_prefix_is_a_repairable_mismatch():
    ns = _ns()
    repair = ns["plan_title_repair"](
        53, "[WP-08][CR] Zavést persistentní DDDA Platform Lab", "WP-12"
    )
    assert repair == {
        "issue": 53,
        "wp": "WP-12",
        "action": "ALIGN_ISSUE_WP_TITLE_PREFIX",
        "from": "[WP-08][CR] Zavést persistentní DDDA Platform Lab",
        "to": "[WP-12][CR] Zavést persistentní DDDA Platform Lab",
    }


def test_other_authority_removes_historical_wp_prefix_but_absence_is_allowed():
    ns = _ns()
    assert ns["aligned_title"]("[WP-08][CR] Artifact Registry", "Other") == (
        "[CR] Artifact Registry"
    )
    assert ns["plan_title_repair"](45, "[CR] Artifact Registry", "Other") is None
    assert ns["plan_title_repair"](49, "[DOC][CR] Dokumentace", "Other") is None


def test_multiple_explicit_wp_prefixes_fail_closed():
    ns = _ns()
    try:
        ns["aligned_title"]("[WP-11][WP-13][CR] Ambiguous", "WP-13")
    except ValueError as exc:
        assert "Ambiguous WP title prefixes" in str(exc)
    else:
        raise AssertionError("multiple WP prefixes must fail closed")


def test_script_records_and_rechecks_presentation_mismatch():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "PRESENTATION_WP_MISMATCH" in text
    assert "ALIGN_ISSUE_WP_TITLE_PREFIX" in text
    assert '"remaining_count": len(remaining)' in text
    assert "final_rows, remaining = inspect(authority)" in text


def test_presentation_evidence_is_bound_to_exact_source_sha():
    script = SCRIPT.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert 'source_sha = cmd("git", "rev-parse", "HEAD")' in script
    assert '"source_sha": source_sha' in script
    assert "assert presentation['source_sha'] == os.environ['GITHUB_SHA']" in workflow

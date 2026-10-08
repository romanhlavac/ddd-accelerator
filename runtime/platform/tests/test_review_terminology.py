"""Prospective review wording contract; historical audit evidence is intentionally untouched."""

from pathlib import Path

from runtime.platform.human_review_evidence import MARKER


ROOT = Path(__file__).resolve().parents[3]


def test_general_and_visual_review_scaffolds_have_distinct_targets():
    template = (ROOT / ".github/PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")
    glossary = (ROOT / "docs/governance/review-terminology.md").read_text(
        encoding="utf-8"
    )

    assert "CR #<cr> → PR #<pr> — READY FOR HUMAN REVIEW" in template
    assert "Human Review PR #<pr>: PASS|CHANGES_REQUIRED" in template
    assert "HVR PR #<pr> / <artifact>: PASS|CHANGES_REQUIRED" in template
    assert "READY FOR HVR" not in template
    assert "HVR #<" not in template
    assert "R<n>" in glossary and "never a Human Review round" in glossary
    assert "Human Visual Review" in glossary and "HRDR" in glossary


def test_machine_review_marker_remains_stable():
    assert MARKER == "<!-- ddda:human-pr-review:v1 -->"

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


def test_human_review_scaffold_uses_three_decision_blocks():
    template = (ROOT / ".github/PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")
    glossary = (ROOT / "docs/governance/review-terminology.md").read_text(
        encoding="utf-8"
    )
    lifecycle = (ROOT / "docs/developer-guide/platform-development-lifecycle.md").read_text(
        encoding="utf-8"
    )
    skill = (ROOT / "knowledge/ddda-platform-development-skill.md").read_text(
        encoding="utf-8"
    )

    for heading in (
        "### Co se mění",
        "### Co se nesmí změnit",
        "### Jaký dluh, riziko nebo výjimku přijímáš",
    ):
        assert heading in template
        assert heading.split("### ", 1)[1] in glossary

    assert "at most three decision points" in template
    assert "questions that require the decision owner's judgment" in template
    assert "Do not ask the human to revalidate technical controls already proven by CI" in template
    assert "validated evidence" in lifecycle
    assert "validated evidence" in skill
    assert "separate from merge authorization" in glossary
    assert "Judgment areas required:" not in template
    assert "[ ] security and isolation" not in template

def test_machine_review_marker_remains_stable():
    assert MARKER == "<!-- ddda:human-pr-review:v1 -->"

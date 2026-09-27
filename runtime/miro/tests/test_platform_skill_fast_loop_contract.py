from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "knowledge" / "ddda-platform-development-skill.md"


def test_platform_skill_requires_global_autonomy_and_truthful_stop_state():
    text = SKILL.read_text(encoding="utf-8")

    required = (
        "Autonomous-by-default platform-development orchestration",
        "every bounded DDDA platform-development assignment",
        "authorized scope",
        "READY FOR HUMAN REVIEW",
        "TECHNICAL FAILURE != HUMAN STOP BOUNDARY",
        "approved alternative execution plane",
        "third related remediation signal",
        "not a new CI gate",
        "Technical PASS cannot imply Human Review PASS",
        "ready-to-copy continuation prompt",
        "single canonical candidate-package identity",
    )
    for marker in required:
        assert marker in text

    assert "must not say or imply" in text
    assert "no real external execution will continue without another user turn" in text

    operating = (ROOT / "docs/developer-guide/chat-work-operating-model.md").read_text(encoding="utf-8")
    assert "schválenou alternativní execution plane" in operating
    assert "zastavit pouze bez dostupné schválené alternativy" in operating
    assert "nikdy netvrdit, že neprovedený read-back či review proběhl" in operating

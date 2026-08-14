from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "knowledge" / "ddda-platform-development-skill.md"


def test_platform_skill_requires_autonomous_fast_loop_and_truthful_stop_state():
    text = SKILL.read_text(encoding="utf-8")

    required = (
        "Autonomous FAST-LOOP orchestration and truthful execution state",
        "Chat/Work owns the mechanical orchestration",
        "Do not ask the human to approve routine transitions",
        "Ask the human only when a human decision or action is genuinely required",
        "Miro MCP quota",
        "ready-to-copy continuation prompt",
        "Merge, promotion, release and tag are never inferred",
    )
    for marker in required:
        assert marker in text

    assert "must not say or imply" in text
    assert "no real external execution will continue without another user turn" in text

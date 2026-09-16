import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "platform" / "Read-DDDAHrdr.py"
SPEC = importlib.util.spec_from_file_location("read_hrdr", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def comment(*, decision="pending", reviewer="romanhlavac", author="github-actions[bot]"):
    return {
        "user": {"login": author},
        "body": "<!-- ddda:human-release-decision:v1 -->\n```json\n"
        + '{"schema_version":1,"decision":"' + decision + '","reviewer":"' + reviewer + '"}\n```',
    }


def test_accepts_one_pending_scaffold_and_human_decision():
    assert MODULE.extract_hrdr([comment()])["decision"] == "pending"
    assert MODULE.extract_hrdr([comment(decision="go", author="romanhlavac")])["decision"] == "go"


def test_rejects_ambiguous_or_spoofed_decision():
    import pytest

    with pytest.raises(ValueError):
        MODULE.extract_hrdr([comment(), comment()])
    with pytest.raises(ValueError):
        MODULE.extract_hrdr([comment(decision="go", author="github-actions[bot]")])

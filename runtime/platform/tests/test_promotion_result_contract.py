from pathlib import Path
import os
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[3]


def test_promotion_wrapper_has_deterministic_result_contract():
    wrapper = (ROOT / "scripts/platform/Invoke-DDDAGovernedPromotePr.ps1").read_text(encoding="utf-8-sig")
    support = (ROOT / "scripts/platform/DDDAPromotionResultSupport.ps1").read_text(encoding="utf-8-sig")
    for field in (
        "promotion_preflight_status",
        "side_effect_assertions_status",
        "wrapper_status",
        "source_sha",
        "candidate_package_sha256",
        "version",
        "release_scope_gate_status",
    ):
        assert field in wrapper
    assert "Get-DDDAPromotionDryRunSnapshot" in wrapper
    assert "Test-DDDAPromotionDryRunSideEffects" in wrapper
    assert "$LASTEXITCODE" not in wrapper
    assert "$LASTEXITCODE" not in support


def test_expected_absence_is_explicit_and_unexpected_failure_is_not_masked():
    support = (ROOT / "scripts/platform/DDDAPromotionResultSupport.ps1").read_text(encoding="utf-8-sig")
    assert 'return "ABSENT"' in support
    assert 'return "ERROR"' in support
    assert "ExpectedAbsentStatus = @(404)" in support
    assert "failed unexpectedly" in support


def test_behavioral_promotion_result_contract():
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if executable is None:
        if os.name == "nt":
            pytest.fail("Windows platform test runtime must expose PowerShell for the promotion result regression")
        pytest.skip("PowerShell is not installed on this non-Windows validation worker")
    script = ROOT / "tests/powershell/Test-DDDAPromotionResultContract.ps1"
    completed = subprocess.run(
        [executable, "-NoProfile", "-File", str(script), "-PlatformPath", str(ROOT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    assert "DDDA promotion result contract: PASS" in completed.stdout

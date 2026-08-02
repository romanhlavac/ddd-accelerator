[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$RepositoryRoot,
    [switch]$NoPush
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = (Resolve-Path -LiteralPath $RepositoryRoot).Path
Set-Location -LiteralPath $root

$before = (git rev-parse HEAD).Trim()
if ($before -notmatch '^[0-9a-f]{40}$') {
    throw "Cannot resolve exact repository HEAD."
}
$dirtyBefore = @(git status --porcelain)
if ($dirtyBefore.Count -ne 0) {
    throw "REM-011 requires a clean working tree before execution.`n$($dirtyBefore -join "`n")"
}

$patcherPath = Join-Path $env:RUNNER_TEMP ("rem-011-patcher-" + [Guid]::NewGuid().ToString("N") + ".py")
$patcher = @'
from __future__ import annotations

import codecs
import re
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
changed: list[str] = []


def read_text(path: Path) -> tuple[str, bool, str]:
    raw = path.read_bytes()
    bom = raw.startswith(codecs.BOM_UTF8)
    text = raw.decode("utf-8-sig")
    newline = "\r\n" if "\r\n" in text else "\n"
    return text.replace("\r\n", "\n"), bom, newline


def write_text(path: Path, text: str, bom: bool, newline: str) -> None:
    normalized = text.replace("\r\n", "\n")
    if newline == "\r\n":
        normalized = normalized.replace("\n", "\r\n")
    payload = normalized.encode("utf-8")
    if bom:
        payload = codecs.BOM_UTF8 + payload
    path.write_bytes(payload)
    rel = path.relative_to(root).as_posix()
    if rel not in changed:
        changed.append(rel)


def replace_literal(text: str, old: str, new: str, *, expected: int, label: str) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"{label}: expected {expected} occurrences, found {count}")
    return text.replace(old, new)


def replace_regex(text: str, pattern: str, replacement: str, *, expected: int, label: str, flags: int = 0) -> str:
    matches = list(re.finditer(pattern, text, flags))
    if len(matches) != expected:
        raise RuntimeError(f"{label}: expected {expected} matches, found {len(matches)}")
    return re.sub(pattern, replacement, text, flags=flags)


def update(path_str: str, transform) -> None:
    path = root / path_str
    text, bom, newline = read_text(path)
    updated = transform(text)
    if updated == text:
        raise RuntimeError(f"{path_str}: transformation produced no change")
    write_text(path, updated, bom, newline)


scaffold_path = "scaffolds/miro/strategic-ddd-method-board.yaml"


def patch_scaffold(text: str) -> str:
    text = replace_literal(
        text,
        "render_contract_version: REM-PR8-HVA-CC-010",
        "render_contract_version: REM-PR8-HVA-CC-011",
        expected=1,
        label="scaffold render contract",
    )
    text = replace_regex(
        text,
        r"(reference_frame_title: Business model canvas - exercise\n\s+reference_frame_url:\s*)https://miro\.com/app/board/uXjVH27wYU4=/",
        r"\1https://miro.com/app/board/uXjVH27wYU4=/?moveToWidget=3458764567890733010",
        expected=3,
        label="Align exact source frame",
    )
    text = replace_regex(
        text,
        r"(reference_frame_title: Starter Modelling Process - Organize\n\s+reference_frame_url:\s*)https://miro\.com/app/board/uXjVH27wYU4=/",
        r"\1https://miro.com/app/board/uXjVH27wYU4=/?moveToWidget=3458764567797253955",
        expected=3,
        label="Organize exact source frame",
    )
    text = replace_regex(
        text,
        r"(reference_frame_title: Starter Modelling Process - Decompose\n\s+reference_frame_url:\s*)https://miro\.com/app/board/uXjVH27wYU4=/",
        r"\1https://miro.com/app/board/uXjVH27wYU4=/?moveToWidget=3458764567797029926",
        expected=1,
        label="Lifecycle exact source frame",
    )

    cookbook_replacements = [
        (
            "https://github.com/romanhlavac/ddd-accelerator/blob/main/docs/methodology/01-metodicky-tok-a-gates.md",
            "https://github.com/romanhlavac/ddd-accelerator/blob/main/docs/cookbooks/08-gate-review.md",
            7,
            "methodology links mislabeled as cookbook",
        ),
        (
            "https://github.com/romanhlavac/ddd-accelerator/blob/main/docs/product/04-synchronizace.md",
            "https://github.com/romanhlavac/ddd-accelerator/blob/main/docs/cookbooks/08-gate-review.md",
            3,
            "product sync links mislabeled as cookbook",
        ),
        (
            "https://github.com/romanhlavac/ddd-accelerator/blob/main/docs/product/01-architektura-ddda.md",
            "https://github.com/romanhlavac/ddd-accelerator/blob/main/docs/cookbooks/05-design-level-eventstorming.md",
            4,
            "product architecture links mislabeled as cookbook",
        ),
    ]
    for old, new, expected, label in cookbook_replacements:
        pattern = rf"(?m)^(\s*cookbook_url:\s*){re.escape(old)}$"
        text = replace_regex(text, pattern, rf"\1{new}", expected=expected, label=label)

    define_pattern = r"(?ms)^  define:\n    items:\n.*?^    sync_policy: ignore\n    connectors: \[\]\n    exclude_from_ingestion: true\n(?=  code:\n)"
    define_replacement = """  define:
    items:
    - id: purpose
      label_cs: PURPOSE
      item_type: shape
      shape: round_rectangle
      x: -1650
      y: 520
      width: 900
      height: 440
      fill_color: '#DDEFA9'
      font_size: 24
    - id: business-decisions
      label_cs: BUSINESS DECISIONS
      item_type: shape
      shape: round_rectangle
      x: -550
      y: 520
      width: 900
      height: 440
      fill_color: '#C7D2FE'
      font_size: 24
    - id: language
      label_cs: UBIQUITOUS LANGUAGE
      item_type: shape
      shape: round_rectangle
      x: 550
      y: 520
      width: 900
      height: 440
      fill_color: '#FDE68A'
      font_size: 24
    - id: communication
      label_cs: INBOUND / OUTBOUND
      item_type: shape
      shape: round_rectangle
      x: 1650
      y: 520
      width: 900
      height: 440
      fill_color: '#BFDBFE'
      font_size: 24
    sync_policy: ignore
    connectors: []
    exclude_from_ingestion: true
"""
    text = replace_regex(
        text,
        define_pattern,
        define_replacement,
        expected=1,
        label="G7 semantic overview roles",
    )
    return text


update(scaffold_path, patch_scaffold)


def patch_render(text: str) -> str:
    old_contract_count = text.count("REM-PR8-HVA-CC-010")
    if old_contract_count < 2:
        raise RuntimeError(f"render contract token: expected at least 2 occurrences, found {old_contract_count}")
    text = text.replace("REM-PR8-HVA-CC-010", "REM-PR8-HVA-CC-011")

    old = '''        if STARTER_REFERENCE_BOARD_ID not in str(row.get("reference_frame_url") or ""):
            failures.append(f"traceability {gate_id} has no exact source frame URL")
'''
    new = '''        source_url = str(row.get("reference_frame_url") or "")
        if STARTER_REFERENCE_BOARD_ID not in source_url:
            failures.append(f"traceability {gate_id} has no exact source frame URL")
        if "?moveToWidget=" not in source_url:
            failures.append(f"traceability {gate_id} must target a concrete DDD Starter frame")
        if "/docs/cookbooks/" not in str(row.get("cookbook_url") or ""):
            failures.append(f"traceability {gate_id} cookbook_url must target docs/cookbooks")
'''
    text = replace_literal(text, old, new, expected=1, label="traceability exact-frame validation")

    old = '''        if len(template.get("items") or []) < int(contract.get("minimum_stage_visual_items", 4)):
            failures.append(f"stage {stage_id} has too few methodological visual items")
'''
    new = '''        template_items = template.get("items") or []
        if len(template_items) < int(contract.get("minimum_stage_visual_items", 4)):
            failures.append(f"stage {stage_id} has too few methodological visual items")
        semantic_ids = [str(item.get("id") or "").strip().casefold() for item in template_items]
        semantic_labels = [re.sub(r"\\s+", " ", str(item.get("label_cs") or "").strip()).casefold() for item in template_items]
        if len(semantic_ids) != len(set(semantic_ids)):
            failures.append(f"stage {stage_id} repeats a semantic visual role")
        if len(semantic_labels) != len(set(semantic_labels)):
            failures.append(f"stage {stage_id} repeats a semantic visual label")
'''
    text = replace_literal(text, old, new, expected=1, label="stage semantic-role validation")

    old = '''        for link_name in ("cookbook_url", "method_url", "starter_reference_url"):
            if not str(stage.get(link_name) or "").startswith("https://"):
                failures.append(f"stage {stage_id} has no usable {link_name}")
'''
    new = '''        for link_name in ("cookbook_url", "method_url", "starter_reference_url"):
            if not str(stage.get(link_name) or "").startswith("https://"):
                failures.append(f"stage {stage_id} has no usable {link_name}")
        if "/docs/cookbooks/" not in str(stage.get("cookbook_url") or ""):
            failures.append(f"stage {stage_id} cookbook_url must target docs/cookbooks")
'''
    text = replace_literal(text, old, new, expected=1, label="stage cookbook classification")

    old = '''        if STARTER_REFERENCE_BOARD_ID not in str(stage.get("reference_frame_url") or ""):
            failures.append(f"stage {stage_id} source URL does not target the DDD Starter board")
'''
    new = '''        stage_source_url = str(stage.get("reference_frame_url") or "")
        if STARTER_REFERENCE_BOARD_ID not in stage_source_url:
            failures.append(f"stage {stage_id} source URL does not target the DDD Starter board")
        if "?moveToWidget=" not in stage_source_url:
            failures.append(f"stage {stage_id} source URL must target a concrete DDD Starter frame")
'''
    text = replace_literal(text, old, new, expected=1, label="stage exact-frame validation")

    old = '''            for field in ("start_cs", "outputs_cs", "cookbook_url", "method_url", "starter_reference_url"):
                if not guide.get(field):
                    failures.append(f"frame {frame_id} guide is missing {field}")
'''
    new = '''            for field in ("start_cs", "outputs_cs", "cookbook_url", "method_url", "starter_reference_url"):
                if not guide.get(field):
                    failures.append(f"frame {frame_id} guide is missing {field}")
            if "/docs/cookbooks/" not in str(guide.get("cookbook_url") or ""):
                failures.append(f"frame {frame_id} guide cookbook_url must target docs/cookbooks")
'''
    text = replace_literal(text, old, new, expected=1, label="frame cookbook classification")

    old = '''                if STARTER_REFERENCE_BOARD_ID not in str(template.get("reference_frame_url") or ""):
                    failures.append(f"example template {template_id} has no exact source frame URL")
'''
    new = '''                example_source_url = str(template.get("reference_frame_url") or "")
                if STARTER_REFERENCE_BOARD_ID not in example_source_url:
                    failures.append(f"example template {template_id} has no exact source frame URL")
                if "?moveToWidget=" not in example_source_url:
                    failures.append(f"example template {template_id} must target a concrete DDD Starter frame")
'''
    text = replace_literal(text, old, new, expected=1, label="example exact-frame validation")
    return text


update("runtime/miro/ddda_miro/render.py", patch_render)


def patch_acceptance(text: str) -> str:
    text = text.replace("REM-PR8-HVA-CC-010", "REM-PR8-HVA-CC-011")
    text = replace_literal(
        text,
        "  business_problem: Vendor lock-in zpomaluje změny a přesouvá znalost mimo organizaci.",
        "  business_problem: Legacy vyhodnocování pojistných událostí skrývá rozhodovací pravidla, zpomaluje vysvětlitelné rozhodnutí a prodražuje bezpečnou změnu.",
        expected=1,
        label="acceptance claims business problem",
    )
    return text


update("scripts/Test-DDDAAcceptance.ps1", patch_acceptance)
update(
    "scripts/platform/Invoke-DDDAMiroAcceptanceEvidence.ps1",
    lambda text: replace_literal(
        text,
        "REM-PR8-HVA-CC-010",
        "REM-PR8-HVA-CC-011",
        expected=1,
        label="Miro evidence fallback contract",
    ),
)

# Replace residual active contract tokens in executable tests/runtime, but preserve historical review documents.
for base in ("runtime", "tests", ".github"):
    for path in (root / base).rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".py", ".ps1", ".yaml", ".yml", ".json"}:
            continue
        text, bom, newline = read_text(path)
        if "REM-PR8-HVA-CC-010" in text:
            write_text(path, text.replace("REM-PR8-HVA-CC-010", "REM-PR8-HVA-CC-011"), bom, newline)


def patch_tests(text: str) -> str:
    marker = "def test_rem_011_hardens_content_coherence_and_exact_traceability"
    if marker in text:
        raise RuntimeError("REM-011 test already exists")
    addition = r'''


def test_rem_011_hardens_content_coherence_and_exact_traceability():
    source = Path(__file__).resolve().parents[3]
    scaffold = load_yaml(source / "scaffolds" / "miro" / "strategic-ddd-method-board.yaml")

    stages = scaffold["method_flow"]["stages"]
    assert [stage["id"] for stage in stages] == [
        "align", "discover", "decompose", "strategize", "connect", "organize", "define", "code",
    ]
    for stage in stages:
        assert "?moveToWidget=" in stage["reference_frame_url"]
        assert "/docs/cookbooks/" in stage["cookbook_url"]

    for row in scaffold["traceability"]:
        assert "?moveToWidget=" in row["reference_frame_url"]
        assert "/docs/cookbooks/" in row["cookbook_url"]

    required_examples = {
        "align", "big_picture", "evidence", "process", "decompose", "lifecycle",
        "strategize", "context_map", "teams", "bc_canvas", "design_es",
    }
    for template_id in required_examples:
        template = scaffold["example_templates"][template_id]
        assert "?moveToWidget=" in template["reference_frame_url"]

    for frame in scaffold["frames"]:
        guide = frame.get("guide") or {}
        if guide:
            assert "/docs/cookbooks/" in guide["cookbook_url"]

    define_items = scaffold["stage_visual_templates"]["define"]["items"]
    assert [item["id"] for item in define_items] == [
        "purpose", "business-decisions", "language", "communication",
    ]
    assert [item["label_cs"] for item in define_items] == [
        "PURPOSE", "BUSINESS DECISIONS", "UBIQUITOUS LANGUAGE", "INBOUND / OUTBOUND",
    ]
    assert len({item["label_cs"].casefold() for item in define_items}) == len(define_items)

    acceptance_source = (source / "scripts" / "Test-DDDAAcceptance.ps1").read_text(encoding="utf-8-sig")
    assert "Vendor lock-in zpomaluje změny" not in acceptance_source
    assert "Legacy vyhodnocování pojistných událostí skrývá rozhodovací pravidla" in acceptance_source
    assert scaffold["visual_contract"]["render_contract_version"] == "REM-PR8-HVA-CC-011"
'''
    return text.rstrip() + addition + "\n"


update("runtime/miro/tests/test_render.py", patch_tests)

review_doc = root / "docs" / "reviews" / "REM-PR8-HVA-CC-011-content-coherence.md"
if review_doc.exists():
    raise RuntimeError(f"Review document already exists: {review_doc}")
review_content = """# REM-PR8-HVA-CC-011 — content coherence and traceability hardening

Status: IMPLEMENTED, PENDING_CI_AND_HUMAN_REVIEW

Date: 2026-08-02

Scope: PR #8, branch `feat/project-steering-and-documentation`

## Důvod změny

REM-010 opravil parent ownership frame `01` a prokázal technickou reprodukovatelnost. Následný pre-review ale našel čtyři zbývající vady: syntetický claims projekt používal obecný vendor-lock problém, Align a Organize odkazovaly pouze na root DDD Starter boardu, overview G7 duplikoval invariantní roli a některé odkazy označené jako kuchařka mířily na metodickou nebo produktovou dokumentaci.

## Implementovaný kontrakt

1. Acceptance Claims Modernization používá claims-specific business problém a jednotný ubiquitous language.
2. Všechny stage, traceability řádky a povinné DDD Starter templates míří na konkrétní `moveToWidget` source frame.
3. G7 overview používá role `PURPOSE`, `BUSINESS DECISIONS`, `UBIQUITOUS LANGUAGE` a `INBOUND / OUTBOUND`.
4. Každý `cookbook_url` míří pod `docs/cookbooks/`; metodika zůstává v `method_url`.
5. Layout validator fail-closed ověřuje exact source frame, klasifikaci cookbook odkazů a neduplicitní stage role.
6. Acceptance test ověřuje doménovou koherenci syntetického claims scénáře.
7. Render contract je `REM-PR8-HVA-CC-011`.

## Exact source frames doplněné v REM-011

- Align — `Business model canvas - exercise`: `3458764567890733010`.
- Organize — `Starter Modelling Process - Organize`: `3458764567797253955`.
- Lifecycle template — `Starter Modelling Process - Decompose`: `3458764567797029926`.

Ostatní stage odkazy zůstávají vázané na již existující exact source frames z REM-010.

## Stav akceptace

Automatizace může potvrdit layout, zdroje, odkazy, UTF-8, idempotenci a obsahovou konzistenci fixture. Nemůže vydat lidské vizuální nebo metodické schválení. Výsledek proto zůstává `PENDING_HUMAN_REVIEW`.

## Zakázané operace

REM-011 neautorizuje merge, promotion, release, tag ani force-push.
"""
write_text(review_doc, review_content, False, "\n")


def patch_docs_index(text: str) -> str:
    old = "- [REM-PR8-HVA-CC-010 — nová human-review revize](reviews/REM-PR8-HVA-CC-010-gap-analysis.md)\n"
    new = old + "- [REM-PR8-HVA-CC-011 — content coherence and traceability hardening](reviews/REM-PR8-HVA-CC-011-content-coherence.md)\n"
    return replace_literal(text, old, new, expected=1, label="documentation index REM-011")


update("docs/README.md", patch_docs_index)


def patch_changelog(text: str) -> str:
    old = "### Changed\n\n"
    new = (
        "### Changed\n\n"
        "- corrective remediation `REM-PR8-HVA-CC-011`: syntetický claims scénář používá jednotný business problém a ubiquitous language; všechny povinné DDD Starter vazby míří na exact `moveToWidget` frame, G7 overview odpovídá Bounded Context Canvasu a odkazy označené jako kuchařka míří výhradně pod `docs/cookbooks/`;\n"
    )
    return replace_literal(text, old, new, expected=1, label="changelog REM-011")


update("CHANGELOG.md", patch_changelog)

traceability_path = root / "docs" / "reference" / "miro-ddd-starter-traceability.md"
trace_text, trace_bom, trace_newline = read_text(traceability_path)
trace_marker = "## REM-011 content coherence hardening"
if trace_marker in trace_text:
    raise RuntimeError("Traceability REM-011 section already exists")
trace_text = trace_text.rstrip() + """

## REM-011 content coherence hardening

Nad rámec parent a layout kontrol z REM-010 platí fail-closed pravidla:

- každý stage a traceability source URL obsahuje konkrétní `moveToWidget`;
- každý povinný DDD Starter example template odkazuje na konkrétní source frame;
- `cookbook_url` smí mířit pouze pod `docs/cookbooks/`, zatímco metodické a knowledge odkazy patří do `method_url`;
- stage mini-vzor nesmí opakovat semantic ID ani normalizovaný label;
- syntetický acceptance projekt musí držet claims-specific business problém, jazyk a artefakty.

G7 overview používá `PURPOSE`, `BUSINESS DECISIONS`, `UBIQUITOUS LANGUAGE` a `INBOUND / OUTBOUND`; invarianty se validují v detailním Design-Level EventStormingu a taktickém návrhu, nikoli jako duplicitní role Bounded Context Canvasu.
""" + "\n"
write_text(traceability_path, trace_text, trace_bom, trace_newline)

adr_path = root / "docs" / "adr" / "0004-miro-redline-traceability-and-frame-01.md"
adr_text, adr_bom, adr_newline = read_text(adr_path)
adr_marker = "## REM-011 addendum"
if adr_marker in adr_text:
    raise RuntimeError("ADR REM-011 addendum already exists")
adr_text = adr_text.rstrip() + """

## REM-011 addendum

REM-011 zpřesňuje Decision bez změny základního ownership modelu: source URL musí mířit na konkrétní Miro frame, `cookbook_url` musí být skutečná kuchařka, stage mini-vzory nesmí duplikovat semantic role a syntetický acceptance příklad musí být obsahově koherentní v jedné doméně. Automatická validace těchto pravidel stále nevytváří lidské gate decision.
""" + "\n"
write_text(adr_path, adr_text, adr_bom, adr_newline)

# Final source-level assertions before tests.
scaffold, _, _ = read_text(root / scaffold_path)
if scaffold.count("?moveToWidget=") < 20:
    raise RuntimeError("REM-011 expected concrete source-frame links were not materialized")
if "REM-PR8-HVA-CC-010" in scaffold:
    raise RuntimeError("Scaffold still declares REM-010")
if "Vendor lock-in zpomaluje změny" in read_text(root / "scripts" / "Test-DDDAAcceptance.ps1")[0]:
    raise RuntimeError("Acceptance fixture still contains the unrelated vendor-lock problem")

print("REM-011 patched files:")
for item in sorted(changed):
    print(item)
'@

try {
    [System.IO.File]::WriteAllText($patcherPath, $patcher, (New-Object System.Text.UTF8Encoding($false)))
    & python $patcherPath $root
    if ($LASTEXITCODE -ne 0) {
        throw "REM-011 source patcher failed with exit code $LASTEXITCODE."
    }
}
finally {
    Remove-Item -LiteralPath $patcherPath -Force -ErrorAction SilentlyContinue
}

Write-Host "Installing targeted Python test dependencies..."
& python -m pip install --disable-pip-version-check -e (Join-Path $root "runtime/miro") pytest
if ($LASTEXITCODE -ne 0) {
    throw "REM-011 dependency setup failed."
}

Write-Host "Running targeted Miro renderer and repository validation tests..."
& python -m pytest (Join-Path $root "runtime/miro/tests/test_render.py") (Join-Path $root "runtime/platform/tests/test_validate_repository.py") -q
if ($LASTEXITCODE -ne 0) {
    throw "REM-011 targeted Python tests failed."
}

Write-Host "Running PowerShell Miro automation regression..."
& pwsh -NoProfile -File (Join-Path $root "tests/powershell/Test-DDDAMiroAutomation.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "REM-011 PowerShell Miro automation regression failed."
}

$diffCheck = @(git diff --check)
if ($LASTEXITCODE -ne 0 -or $diffCheck.Count -ne 0) {
    throw "REM-011 git diff check failed.`n$($diffCheck -join "`n")"
}

# The transport script is one-shot and must not remain in the resulting product tree.
Remove-Item -LiteralPath $PSCommandPath -Force

git add -A
$staged = @(git diff --cached --name-only)
if ($staged.Count -lt 7) {
    throw "REM-011 staged an unexpectedly small change set: $($staged.Count) files."
}
if ($staged -contains "scripts/remediation/REM-PR8-HVA-CC-011.ps1") {
    # Deletion of the transport script is expected and is represented in the staged diff.
    $scriptStatus = @(git diff --cached --name-status -- "scripts/remediation/REM-PR8-HVA-CC-011.ps1")
    if (-not ($scriptStatus -match '^D\s')) {
        throw "REM-011 transport script was not staged for deletion."
    }
}

$commitMessage = "fix(miro): harden REM-011 content coherence and traceability"
git commit -m $commitMessage
if ($LASTEXITCODE -ne 0) {
    throw "REM-011 commit failed."
}

$after = (git rev-parse HEAD).Trim()
if ($after -eq $before) {
    throw "REM-011 did not create a commit."
}
$commitCount = [int](git rev-list --count "$before..$after")
if ($commitCount -ne 1) {
    throw "REM-011 must create exactly one validated implementation commit; created $commitCount."
}
$dirtyAfter = @(git status --porcelain)
if ($dirtyAfter.Count -ne 0) {
    throw "REM-011 left a dirty working tree.`n$($dirtyAfter -join "`n")"
}

$evidenceRoot = Join-Path $env:LOCALAPPDATA "DDDA/remediation-checks/REM-PR8-HVA-CC-011"
New-Item -ItemType Directory -Force -Path $evidenceRoot | Out-Null
[ordered]@{
    status = "PASS"
    remediation = "REM-PR8-HVA-CC-011"
    before_sha = $before
    after_sha = $after
    commit_count = $commitCount
    commit_message = $commitMessage
    branch = (git branch --show-current).Trim()
    tests = @(
        "runtime/miro/tests/test_render.py",
        "runtime/platform/tests/test_validate_repository.py",
        "tests/powershell/Test-DDDAMiroAutomation.ps1"
    )
    human_visual_acceptance = "PENDING"
    merge = $false
    promotion = $false
    release = $false
    tag = $false
    force_push = $false
    created_at = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $evidenceRoot "result.json") -Encoding UTF8

Write-Host "REM-011 implementation commit: $after"
if (-not $NoPush) {
    throw "REM-011 is governed by the remote broker and must be invoked with -NoPush."
}

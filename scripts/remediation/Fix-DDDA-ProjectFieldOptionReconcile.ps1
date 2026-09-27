[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repositoryRoot = (& git rev-parse --show-toplevel).Trim()
if ([string]::IsNullOrWhiteSpace($repositoryRoot)) {
    throw "Cannot resolve repository root."
}
Push-Location $repositoryRoot
try {
    if ((& git status --porcelain).Count -ne 0) {
        throw "Remediation requires a clean working tree."
    }

    $python = if (Get-Command python -ErrorAction SilentlyContinue) {
        "python"
    }
    elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
        "python3"
    }
    else {
        throw "Python is required for deterministic source patching."
    }

    $patchScript = Join-Path ([System.IO.Path]::GetTempPath()) ("ddda-project-option-reconcile-" + [Guid]::NewGuid().ToString("N") + ".py")
    $patch = @'
from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8-sig")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one match in {path}, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


core = Path("scripts/platform/Reconcile-DDDAProjectBacklogCore.py")
core_anchor = '''def create_view(project_id, name, filter_value):
    q = """mutation($projectId:ID!,$name:String!){createProjectV2View(input:{projectId:$projectId,name:$name,layout:TABLE_LAYOUT}){projectV2View{id number name layout filter}}}"""
    created = gql(q, {"projectId": project_id, "name": name})["data"]["createProjectV2View"]["projectV2View"]
    return update_view(created["id"], name, filter_value)


def resolve_project(repairs):
'''
core_replacement = '''def create_view(project_id, name, filter_value):
    q = """mutation($projectId:ID!,$name:String!){createProjectV2View(input:{projectId:$projectId,name:$name,layout:TABLE_LAYOUT}){projectV2View{id number name layout filter}}}"""
    created = gql(q, {"projectId": project_id, "name": name})["data"]["createProjectV2View"]["projectV2View"]
    return update_view(created["id"], name, filter_value)


def project_option_input(option):
    item = {
        "name": option["name"],
        "color": option.get("color") or "GRAY",
        "description": option.get("description") or "",
    }
    if option.get("id"):
        item["id"] = option["id"]
    return item


def reconcile_configured_project_options(cfg, project_number, fields, repairs):
    changed = False
    q = """mutation($fieldId:ID!,$options:[ProjectV2SingleSelectFieldOptionInput!]!){updateProjectV2Field(input:{fieldId:$fieldId,singleSelectOptions:$options}){projectV2Field{... on ProjectV2FieldCommon{id name}}}}"""
    for definition in cfg.get("fields", []):
        if definition.get("type") != "SINGLE_SELECT":
            continue
        field_name = definition["name"]
        field = fields.get(field_name)
        if not field:
            continue
        existing = list(field.get("options") or [])
        existing_names = {x.get("name") for x in existing}
        missing = [
            option
            for option in definition.get("options", [])
            if option.get("name") not in existing_names
        ]
        if not missing:
            continue
        options = [project_option_input(option) for option in existing]
        options.extend(project_option_input(option) for option in missing)
        gql(q, {"fieldId": field["id"], "options": options})
        repairs.append(
            {
                "project": project_number,
                "action": "ADD_PROJECT_FIELD_OPTIONS",
                "field": field_name,
                "value": [option["name"] for option in missing],
            }
        )
        changed = True
    return changed


def resolve_project(repairs):
'''
replace_once(core, core_anchor, core_replacement)

resolve_anchor = '''    fields = {x.get("name"): x for x in p["fields"]["nodes"] if x.get("name")}
    return number, p["id"], fields, p["views"]["nodes"]
'''
resolve_replacement = '''    fields = {x.get("name"): x for x in p["fields"]["nodes"] if x.get("name")}
    cfg = json.loads(CFG_PATH.read_text(encoding="utf-8-sig"))
    if reconcile_configured_project_options(cfg, number, fields, repairs):
        p = gql(Q_PROJECT, {"login": OWNER, "number": number})["data"]["user"]["projectV2"]
        fields = {x.get("name"): x for x in p["fields"]["nodes"] if x.get("name")}
    return number, p["id"], fields, p["views"]["nodes"]
'''
replace_once(core, resolve_anchor, resolve_replacement)

verify_anchor = '''    if p["title"] != PROJECT_TITLE:
        problems.append({"result": "PROJECT_TITLE_MISMATCH", "actual": p["title"], "expected": PROJECT_TITLE})
    by_name = {v["name"]: v for v in p["views"]["nodes"]}
'''
verify_replacement = '''    if p["title"] != PROJECT_TITLE:
        problems.append({"result": "PROJECT_TITLE_MISMATCH", "actual": p["title"], "expected": PROJECT_TITLE})
    fields = {x.get("name"): x for x in p["fields"]["nodes"] if x.get("name")}
    cfg = json.loads(CFG_PATH.read_text(encoding="utf-8-sig"))
    for definition in cfg.get("fields", []):
        if definition.get("type") != "SINGLE_SELECT":
            continue
        field_name = definition["name"]
        field = fields.get(field_name)
        if not field:
            problems.append({"result": "MISSING_PROJECT_FIELD", "field": field_name})
            continue
        actual = {option.get("name") for option in field.get("options", [])}
        missing = [
            option["name"]
            for option in definition.get("options", [])
            if option.get("name") not in actual
        ]
        if missing:
            problems.append(
                {
                    "result": "MISSING_PROJECT_FIELD_OPTIONS",
                    "field": field_name,
                    "missing": missing,
                }
            )
    by_name = {v["name"]: v for v in p["views"]["nodes"]}
'''
replace_once(core, verify_anchor, verify_replacement)


test_file = Path("runtime/platform/tests/test_project_backlog_delivery_governance.py")
test_anchor = '''def test_project_view_creation_uses_supported_graphql_contract():
'''
test_block = '''def test_reconciler_materializes_missing_configured_project_options_without_dropping_existing_options():
    ns = runpy.run_path(
        str(RECONCILER_CORE),
        run_name="ddda_project_option_reconcile_contract_test",
    )
    calls = []

    def fake_gql(query, variables=None):
        calls.append((query, variables or {}))
        return {
            "data": {
                "updateProjectV2Field": {
                    "projectV2Field": {"id": "FIELD-1", "name": "Work Package"}
                }
            }
        }

    ns["gql"] = fake_gql
    fields = {
        "Work Package": {
            "id": "FIELD-1",
            "name": "Work Package",
            "dataType": "SINGLE_SELECT",
            "options": [
                {"id": "OPT-08", "name": "WP-08", "color": "BLUE", "description": "foundation"},
                {"id": "OPT-LEGACY", "name": "Legacy", "color": "GRAY", "description": "preserve"},
            ],
        }
    }
    cfg = {
        "fields": [
            {
                "name": "Work Package",
                "type": "SINGLE_SELECT",
                "options": [
                    {"name": "WP-08", "color": "BLUE", "description": "foundation"},
                    {"name": "WP-14", "color": "GREEN", "description": "workbench"},
                ],
            }
        ]
    }
    repairs = []

    changed = ns["reconcile_configured_project_options"](cfg, 7, fields, repairs)

    assert changed is True
    assert len(calls) == 1
    mutation, variables = calls[0]
    assert "updateProjectV2Field" in mutation
    assert variables["fieldId"] == "FIELD-1"
    assert [option["name"] for option in variables["options"]] == ["WP-08", "Legacy", "WP-14"]
    assert variables["options"][0]["id"] == "OPT-08"
    assert variables["options"][1]["id"] == "OPT-LEGACY"
    assert "id" not in variables["options"][2]
    assert repairs == [
        {
            "project": 7,
            "action": "ADD_PROJECT_FIELD_OPTIONS",
            "field": "Work Package",
            "value": ["WP-14"],
        }
    ]


def test_reconciler_does_not_mutate_project_options_when_contract_is_already_satisfied():
    ns = runpy.run_path(
        str(RECONCILER_CORE),
        run_name="ddda_project_option_reconcile_noop_contract_test",
    )
    calls = []
    ns["gql"] = lambda *args, **kwargs: calls.append((args, kwargs))
    fields = {
        "Work Package": {
            "id": "FIELD-1",
            "options": [
                {"id": "OPT-14", "name": "WP-14", "color": "GREEN", "description": "workbench"}
            ],
        }
    }
    cfg = {
        "fields": [
            {
                "name": "Work Package",
                "type": "SINGLE_SELECT",
                "options": [
                    {"name": "WP-14", "color": "GREEN", "description": "workbench"}
                ],
            }
        ]
    }
    repairs = []

    changed = ns["reconcile_configured_project_options"](cfg, 7, fields, repairs)

    assert changed is False
    assert calls == []
    assert repairs == []


def test_project_view_creation_uses_supported_graphql_contract():
'''
replace_once(test_file, test_anchor, test_block)

fragments_anchor = '''        "PRESENTATION_WP_MISMATCH",
        '"remaining_count": 0',
'''
fragments_replacement = '''        "PRESENTATION_WP_MISMATCH",
        "ADD_PROJECT_FIELD_OPTIONS",
        "MISSING_PROJECT_FIELD_OPTIONS",
        '"remaining_count": 0',
'''
replace_once(test_file, fragments_anchor, fragments_replacement)


doc = Path("docs/governance/wp-backlog-consistency.md")
doc_anchor = '''- Project title je přesně `DDDA Platform Backlog & Delivery`.
- Planning view je `Plánování a Backlog`, `TABLE`, filter `is:issue`.
'''
doc_replacement = '''- Project title je přesně `DDDA Platform Backlog & Delivery`.
- Privileged reconciler před item projection mechanicky doplní chybějící canonical `SINGLE_SELECT` options z verzovaného `github-bootstrap.json`, zachová existující live option IDs i případné další live options a fresh read-back musí prokázat přítomnost všech canonical options.
- Planning view je `Plánování a Backlog`, `TABLE`, filter `is:issue`.
'''
replace_once(doc, doc_anchor, doc_replacement)

fail_anchor = '''- Project title nebo některá kanonická view/filter projekce neodpovídá kontraktu;
- nezdůvodněná legacy výjimka;
'''
fail_replacement = '''- Project title nebo některá kanonická view/filter projekce neodpovídá kontraktu;
- canonical `SINGLE_SELECT` option z verzovaného Project contractu po reconciliation chybí (`MISSING_PROJECT_FIELD_OPTIONS`);
- nezdůvodněná legacy výjimka;
'''
replace_once(doc, fail_anchor, fail_replacement)


changelog = Path("CHANGELOG.md")
changelog_anchor = '''### Fixed

- controlled promotion now accepts only the already revalidated exact
'''
changelog_replacement = '''### Fixed

- privileged backlog reconciliation now materializes missing canonical GitHub Project single-select options from the versioned contract before item projection and verifies them on fresh read-back, preventing a newly versioned Work Package such as `WP-14` from failing at the first item update.

- controlled promotion now accepts only the already revalidated exact
'''
replace_once(changelog, changelog_anchor, changelog_replacement)
'@

    [System.IO.File]::WriteAllText($patchScript, $patch, (New-Object System.Text.UTF8Encoding($false)))
    try {
        & $python $patchScript
        if ($LASTEXITCODE -ne 0) {
            throw "Deterministic source patch failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Remove-Item -LiteralPath $patchScript -Force -ErrorAction SilentlyContinue
    }

    & $python -m py_compile scripts/platform/Reconcile-DDDAProjectBacklogCore.py
    if ($LASTEXITCODE -ne 0) { throw "Core reconciler compile validation failed." }

    & $python -m pytest -q runtime/platform/tests/test_project_backlog_delivery_governance.py
    if ($LASTEXITCODE -ne 0) { throw "Governance regression tests failed." }

    & $python -m json.tool config/governance/github-bootstrap.json | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Versioned Project contract is invalid JSON." }

    $allowed = @(
        "CHANGELOG.md",
        "docs/governance/wp-backlog-consistency.md",
        "runtime/platform/tests/test_project_backlog_delivery_governance.py",
        "scripts/platform/Reconcile-DDDAProjectBacklogCore.py",
        "scripts/remediation/Fix-DDDA-ProjectFieldOptionReconcile.ps1"
    )
    $changed = @(& git status --porcelain | ForEach-Object { $_.Substring(3).Trim() })
    $unexpected = @($changed | Where-Object { $_ -notin $allowed })
    if ($unexpected.Count -gt 0) {
        throw "Unexpected remediation paths: $($unexpected -join ', ')"
    }

    Remove-Item -LiteralPath $PSCommandPath -Force
}
finally {
    Pop-Location
}

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
import copy
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import tempfile

try:
    from ruamel.yaml import YAML
except ImportError as exc:  # pragma: no cover - explicit runtime diagnostic
    raise RuntimeError("ddda-steering vyžaduje ruamel.yaml. Spusť Install-DDDASteeringRuntime.ps1.") from exc

YAML_RT = YAML()
YAML_RT.preserve_quotes = True
YAML_RT.default_flow_style = False
YAML_RT.width = 4096
YAML_SAFE = YAML(typ="safe")

STAGES = ["align", "discover", "decompose", "strategize", "connect", "organize", "define", "code"]
GATES = [f"G{i}" for i in range(1, 9)]
NEXT_STAGE = {gate: STAGES[index + 1] if index + 1 < len(STAGES) else "code" for index, gate in enumerate(GATES)}
HUMAN_DECISION_OUTCOMES = {"passed", "conditional", "rejected"}
AUTOMATION_IDENTITY = re.compile(
    r"(?i)(^|[\s._-])(acceptance\s*runner|ci|bot|automation|automated|pipeline|github\s*actions?)([\s._-]|$)"
)


class SteeringError(ValueError):
    pass


@dataclass(frozen=True)
class EvidenceResult:
    gate: str
    status: str
    present: list[str]
    missing: list[str]


@dataclass(frozen=True)
class DecisionValidation:
    valid: bool
    reasons: list[str]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_yaml(path: Path) -> Any:
    if not path.exists():
        raise SteeringError(f"Soubor neexistuje: {path}")
    with path.open("r", encoding="utf-8-sig") as handle:
        data = YAML_SAFE.load(handle)
    return data if data is not None else {}


def dump_yaml(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        YAML_RT.dump(data, handle)


def _required_text(value: Any, path: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise SteeringError(f"Povinná hodnota chybí: {path}")
    return text


def _string_list(value: Any, path: str, *, required: bool = False) -> list[str]:
    if value is None:
        result: list[str] = []
    elif isinstance(value, list):
        result = [str(item).strip() for item in value if str(item).strip()]
    else:
        raise SteeringError(f"{path} musí být YAML seznam.")
    if required and not result:
        raise SteeringError(f"Povinný seznam je prázdný: {path}")
    return result


def _git(project_root: Path, *arguments: str, check: bool = True) -> str:
    process = subprocess.run(
        ["git", "-C", str(project_root), *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and process.returncode != 0:
        detail = (process.stderr or process.stdout).strip()
        raise SteeringError(f"Git příkaz selhal v projektu: git {' '.join(arguments)}\n{detail}")
    return process.stdout.strip()


def _git_head(project_root: Path) -> str:
    commit = _git(project_root, "rev-parse", "HEAD")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise SteeringError("Gate review vyžaduje projekt s platným Git HEAD commitem.")
    return commit


def _assert_clean_project(project_root: Path) -> None:
    status = _git(project_root, "status", "--porcelain")
    if status:
        raise SteeringError(
            "Gate review vyžaduje čistý projektový Git working tree. "
            "Nejprve zkontroluj a commitni nebo odlož změny."
        )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _project_manifest(project_root: Path) -> dict[str, Any]:
    manifest = load_yaml(project_root / "project.yaml")
    if not isinstance(manifest, dict):
        raise SteeringError("project.yaml musí obsahovat objekt.")
    return manifest


def _project_id(project_root: Path) -> str:
    manifest = _project_manifest(project_root)
    return _required_text((manifest.get("project") or {}).get("id"), "project.id")


def _project_scope_hash(project_root: Path) -> str:
    manifest = _project_manifest(project_root)
    return _canonical_sha256(
        {
            "project_id": (manifest.get("project") or {}).get("id"),
            "scope": manifest.get("scope") or {},
            "owners": manifest.get("owners") or {},
        }
    )


def _artifact_hashes(project_root: Path, relative_paths: Iterable[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for relative in sorted(set(relative_paths)):
        path = project_root / relative
        if not path.is_file():
            raise SteeringError(f"Evidence soubor pro gate neexistuje: {relative}")
        result[relative] = _file_sha256(path)
    return result


def _human_identity(value: Any, path: str) -> str:
    text = _required_text(value, path)
    if AUTOMATION_IDENTITY.search(text):
        raise SteeringError(f"{path} musí být konkrétní lidská identita; automatizační identita '{text}' není povolena.")
    return text


def _decision_owner(project_root: Path, value: Any) -> str:
    owner = _required_text(value, "gate_decision.decision_owner")
    manifest = _project_manifest(project_root)
    owners = manifest.get("owners") or {}
    if not isinstance(owners, dict):
        raise SteeringError("project.yaml owners musí být objekt.")
    allowed: set[str] = set()
    for role, identity in owners.items():
        identity_text = str(identity or "").strip()
        if identity_text:
            allowed.add(str(role).strip().casefold())
            allowed.add(identity_text.casefold())
    if not allowed:
        raise SteeringError("Gate nelze rozhodnout; project.yaml neobsahuje konkrétního decision ownera.")
    if owner.casefold() not in allowed:
        raise SteeringError(
            "gate_decision.decision_owner musí odpovídat explicitní roli nebo identitě v project.yaml owners."
        )
    return owner


def _is_test_fixture(project_root: Path) -> bool:
    marker = project_root / ".ddda" / "test-fixture"
    if os.environ.get("DDDA_GATE_TEST_SIMULATION") != "1" or not marker.is_file():
        return False
    try:
        project_root.resolve().relative_to(Path(tempfile.gettempdir()).resolve())
        return True
    except ValueError:
        return False


def normalize_intake(raw: dict[str, Any], project_types: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict) or not isinstance(raw.get("intake"), dict):
        raise SteeringError("Intake musí obsahovat kořenový objekt 'intake'.")
    source = raw["intake"]
    project_id = _required_text(source.get("project_id"), "intake.project_id")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}", project_id):
        raise SteeringError("intake.project_id musí být lowercase slug o délce 2–63 znaků.")
    project_type = _required_text(source.get("type"), "intake.type")
    if project_type not in project_types:
        allowed = ", ".join(sorted(project_types))
        raise SteeringError(f"Neznámý typ projektu '{project_type}'. Povolené typy: {allowed}")
    scope = source.get("scope") or {}
    if not isinstance(scope, dict):
        raise SteeringError("intake.scope musí být objekt s poli in/out.")
    owners = source.get("owners") or {}
    if not isinstance(owners, dict):
        raise SteeringError("intake.owners musí být objekt.")
    normalized = {
        "intake": {
            "schema_version": 1,
            "project_id": project_id,
            "name": _required_text(source.get("name"), "intake.name"),
            "type": project_type,
            "type_alias": source.get("type_alias"),
            "business_problem": _required_text(source.get("business_problem"), "intake.business_problem"),
            "decision_to_enable": _required_text(source.get("decision_to_enable"), "intake.decision_to_enable"),
            "goal": _required_text(source.get("goal"), "intake.goal"),
            "scope": {
                "in": _string_list(scope.get("in"), "intake.scope.in", required=True),
                "out": _string_list(scope.get("out"), "intake.scope.out"),
            },
            "actors": _string_list(source.get("actors"), "intake.actors", required=True),
            "constraints": _string_list(source.get("constraints"), "intake.constraints"),
            "assumptions": _string_list(source.get("assumptions"), "intake.assumptions"),
            "quality_attributes": _string_list(source.get("quality_attributes"), "intake.quality_attributes", required=True),
            "existing_systems": _string_list(source.get("existing_systems"), "intake.existing_systems"),
            "teams": _string_list(source.get("teams"), "intake.teams"),
            "sources": _string_list(source.get("sources"), "intake.sources"),
            "owners": {str(key): (None if value is None else str(value)) for key, value in owners.items()},
            "classification": copy.deepcopy(source.get("classification") or {"data_sensitivity": "internal", "contains_health_data": False}),
        }
    }
    return normalized


def load_config(platform_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    config_root = platform_root / "config" / "steering"
    project_types_doc = load_yaml(config_root / "project-types.yaml")
    gates_doc = load_yaml(config_root / "gates.yaml")
    journey_doc = load_yaml(config_root / "journey-map.yaml")
    return (
        project_types_doc.get("project_types") or {},
        gates_doc.get("gates") or {},
        journey_doc,
    )


def intake_summary(intake_path: Path, platform_root: Path) -> dict[str, Any]:
    project_types, _, _ = load_config(platform_root)
    return normalize_intake(load_yaml(intake_path), project_types)["intake"]


def _managed_artifact(
    artifact_id: str,
    artifact_type: str,
    name: str,
    description: str,
    stage: str,
    status: str = "candidate",
    **extra: Any,
) -> dict[str, Any]:
    miro = copy.deepcopy(extra.pop("miro", None) or {"item_type": "sticky_note"})
    miro.setdefault("item_type", "sticky_note")
    artifact = {
        "id": artifact_id,
        "type": artifact_type,
        "name": name,
        "description": description,
        "status": status,
        "stage": stage,
        "miro": miro,
    }
    artifact.update(extra)
    return {"artifact": artifact}


def _tailoring(project_type: str, cfg: dict[str, Any]) -> dict[str, Any]:
    selected = cfg.get("stages") or STAGES
    selected = [stage for stage in STAGES if stage in selected]
    return {
        "schema_version": 1,
        "profile": project_type,
        "starter_method": "align-discover-decompose-strategize-connect-organize-define-code",
        "selected_stages": [
            {
                "stage": stage,
                "gate": f"G{STAGES.index(stage) + 1}",
                "required": True,
                "rationale": (cfg.get("rationale") or {}).get(stage, "Součást kanonické DDD starter metodiky."),
            }
            for stage in selected
        ],
        "extensions": list(cfg.get("extensions") or []),
        "skipped_stages": [stage for stage in STAGES if stage not in selected],
        "rule": "Tailoring může fázi zúžit nebo odložit, ale nesmí tiše označit chybějící evidence za splněné.",
    }


def _gate_record(gate: str, gate_cfg: dict[str, Any]) -> dict[str, Any]:
    stage = gate_cfg.get("stage") or STAGES[int(gate[1:]) - 1]
    return {
        "gate": {
            "id": gate,
            "stage": stage,
            "question": gate_cfg.get("question", ""),
            "status": "not_ready",
            "evidence": {"present": [], "missing": list(gate_cfg.get("evidence") or []), "disputed": []},
            "approvals": {"business_owner": "pending", "architecture_owner": "pending"},
            "conditions": [],
            "decision": None,
            "reviewed_at": None,
            "reviewed_by": None,
            "note": None,
        }
    }


def update_project_manifest(project_root: Path, intake: dict[str, Any], tailoring: dict[str, Any]) -> None:
    path = project_root / "project.yaml"
    with path.open("r", encoding="utf-8-sig") as handle:
        manifest = YAML_RT.load(handle)
    manifest.setdefault("workflow", {})
    manifest["workflow"]["profile"] = intake["type"]
    manifest["workflow"]["current_stage"] = tailoring["selected_stages"][0]["stage"]
    manifest["workflow"]["completed_gates"] = []
    manifest["workflow"]["extensions"] = list(tailoring.get("extensions") or [])
    manifest["scope"] = copy.deepcopy(intake["scope"])
    manifest["quality_attributes"] = list(intake["quality_attributes"])
    manifest["owners"] = copy.deepcopy(intake["owners"])
    manifest["classification"] = copy.deepcopy(intake["classification"])
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        YAML_RT.dump(manifest, handle)


def bootstrap(
    project_root: Path,
    intake_path: Path,
    platform_root: Path,
    *,
    preserve_project_manifest: bool = False,
) -> dict[str, Any]:
    project_types, gates_cfg, journey = load_config(platform_root)
    normalized = normalize_intake(load_yaml(intake_path), project_types)
    intake = normalized["intake"]
    project_manifest = load_yaml(project_root / "project.yaml")
    manifest_id = str((project_manifest.get("project") or {}).get("id") or "")
    if manifest_id != intake["project_id"]:
        raise SteeringError(f"Project ID v intake '{intake['project_id']}' neodpovídá project.yaml '{manifest_id}'.")

    profile_cfg = project_types[intake["type"]]
    tailoring = _tailoring(intake["type"], profile_cfg)
    dump_yaml(normalized, project_root / "project-intake.yaml")
    dump_yaml(
        {
            "profile": {
                "schema_version": 1,
                "project_id": intake["project_id"],
                "name": intake["name"],
                "type": intake["type"],
                "business_problem": intake["business_problem"],
                "decision_to_enable": intake["decision_to_enable"],
                "goal": intake["goal"],
                "created_at": now_utc(),
            }
        },
        project_root / "project-profile.yaml",
    )
    dump_yaml(tailoring, project_root / "lifecycle-tailoring.yaml")
    if preserve_project_manifest:
        dump_yaml(
            {
                "adoption": {
                    "schema_version": 1,
                    "mode": "legacy-resume",
                    "project_id": intake["project_id"],
                    "baseline": "pre-steering-workspace-v1",
                    "preserved_project_manifest": True,
                    "adopted_at": now_utc(),
                }
            },
            project_root / ".ddda" / "adoption.yaml",
        )
    else:
        update_project_manifest(project_root, intake, tailoring)

    charter = _managed_artifact(
        f"{intake['project_id']}.project-charter",
        "project-charter",
        "Project charter",
        intake["business_problem"],
        "align",
        status="candidate",
        business_problem=intake["business_problem"],
        decision_to_enable=intake["decision_to_enable"],
        goal=intake["goal"],
        scope=intake["scope"],
        actors=intake["actors"],
        constraints=intake["constraints"],
        assumptions=intake["assumptions"],
        owners=intake["owners"],
        sources=intake["sources"],
        miro={
            "item_type": "sticky_note",
            "frame_id": "control-center",
            "position": {"x": -1200, "y": 450, "origin": "center"},
            "geometry": {"width": 1050},
            "style": {"fillColor": "light_yellow"},
        },
    )
    dump_yaml(charter, project_root / "artifacts" / "align" / "project-charter.yaml")

    for gate in GATES:
        path = project_root / "decisions" / "gates" / f"{gate}.yaml"
        if not path.exists():
            dump_yaml(_gate_record(gate, gates_cfg.get(gate) or {}), path)

    session = {
        "session": {
            "schema_version": 1,
            "scope": "project",
            "active_project": intake["project_id"],
            "starter_method": tailoring["starter_method"],
            "read_first": [
                "project.yaml",
                "project-intake.yaml",
                "lifecycle-tailoring.yaml",
                "artifacts/status/current-status.yaml",
                "knowledge/00-knowledge-index.md",
            ],
            "write_boundaries": {
                "allowed": ["project.yaml", "project-intake.yaml", "project-profile.yaml", "lifecycle-tailoring.yaml", "ingestion/", "artifacts/", "decisions/", "workshops/", "miro/", "reports/", ".ddda/"],
                "forbidden": ["platform repository", "secrets", "implicit Git push", "implicit gate approval"],
            },
        }
    }
    dump_yaml(session, project_root / ".ddda" / "session-context.yaml")
    contract = {
        "agent_contract": {
            "id": "project-orchestrator",
            "name": "DDDA project orchestrator",
            "role": "Navrhuje další krok a spouští pouze potvrzené deterministické operace.",
            "inputs": ["project-intake.yaml", "project.yaml", "lifecycle-tailoring.yaml", "artifacts/status/current-status.yaml"],
            "outputs": ["artifacts/", "decisions/gates/", "reports/"],
            "allowed_write_paths": ["project.yaml", "artifacts/", "decisions/", "workshops/", "miro/", "reports/", ".ddda/"],
            "forbidden_actions": ["approve_gate_without_human", "push_without_confirmation", "resolve_semantic_conflict_by_last_write_wins"],
            "validation": ["schema", "evidence", "git_diff", "dry_run_before_miro_write"],
            "handoff_rules": ["facts_keep_source", "hypotheses_remain_candidate", "decisions_need_owner"],
            "downstream_consumers": ["chat", "gate-review", "miro-sync", "git-review"],
        }
    }
    dump_yaml(contract, project_root / ".ddda" / "agent-contract.yaml")
    dump_yaml(journey, project_root / ".ddda" / "journey-map.yaml")
    return generate_status(project_root, platform_root)


def _matches(project_root: Path, pattern: str) -> list[str]:
    normalized = pattern.replace("\\", "/")
    matches: list[str] = []
    for path in project_root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(project_root).as_posix()
        if fnmatch.fnmatch(relative, normalized):
            matches.append(relative)
    return sorted(matches)


def evaluate_gate(project_root: Path, gate: str, gate_cfg: dict[str, Any]) -> EvidenceResult:
    present: list[str] = []
    missing: list[str] = []
    for pattern in gate_cfg.get("evidence") or []:
        found = _matches(project_root, pattern)
        if found:
            present.extend(found)
        else:
            missing.append(pattern)
    return EvidenceResult(gate=gate, status="ready_for_review" if not missing else "not_ready", present=sorted(set(present)), missing=missing)


def _load_gate_record(project_root: Path, gate: str, gate_cfg: dict[str, Any]) -> dict[str, Any]:
    path = project_root / "decisions" / "gates" / f"{gate}.yaml"
    if path.exists():
        return load_yaml(path)
    return _gate_record(gate, gate_cfg)


def _read_workflow(project_root: Path) -> dict[str, Any]:
    manifest = load_yaml(project_root / "project.yaml")
    return copy.deepcopy(manifest.get("workflow") or {})


def validate_gate_decision(project_root: Path, gate: str, gate_data: dict[str, Any], evidence: EvidenceResult) -> DecisionValidation:
    status = str(gate_data.get("status") or "")
    if status not in HUMAN_DECISION_OUTCOMES:
        return DecisionValidation(valid=False, reasons=["gate nemá lidské rozhodnutí"])

    decision = gate_data.get("decision")
    if not isinstance(decision, dict):
        return DecisionValidation(valid=False, reasons=["chybí strukturovaný gate_decision record"])

    reasons: list[str] = []
    provenance = str(decision.get("provenance") or "")
    if provenance == "test_simulation":
        if not _is_test_fixture(project_root):
            reasons.append("test_simulation není povolena pro běžný projekt")
    elif provenance != "human":
        reasons.append("provenance není human")

    for field in ("project_id", "scope", "decision_owner", "reviewer", "approver", "decided_at"):
        if not str(decision.get(field) or "").strip():
            reasons.append(f"chybí decision.{field}")

    if str(decision.get("project_id") or "") != _project_id(project_root):
        reasons.append("decision project_id neodpovídá projektu")

    if provenance == "human":
        for field in ("reviewer", "approver"):
            value = str(decision.get(field) or "")
            if value and AUTOMATION_IDENTITY.search(value):
                reasons.append(f"decision.{field} používá automatizační identitu")
        try:
            _decision_owner(project_root, decision.get("decision_owner"))
        except SteeringError as exc:
            reasons.append(str(exc))

    evidence_record = decision.get("evidence") or {}
    project_commit = str(evidence_record.get("project_commit") or "")
    if not re.fullmatch(r"[0-9a-f]{40}", project_commit):
        reasons.append("decision.evidence.project_commit není platný SHA")
    else:
        current_head = _git_head(project_root)
        ancestor = subprocess.run(
            ["git", "-C", str(project_root), "merge-base", "--is-ancestor", project_commit, current_head],
            check=False,
            capture_output=True,
        )
        if ancestor.returncode != 0:
            reasons.append("reviewed project commit není předkem aktuálního HEAD")

    if str(evidence_record.get("scope_sha256") or "") != _project_scope_hash(project_root):
        reasons.append("scope nebo decision ownership se od review změnily")

    recorded_hashes = evidence_record.get("artifact_hashes") or {}
    if not isinstance(recorded_hashes, dict):
        reasons.append("evidence artifact_hashes musí být objekt")
    elif evidence.present and not recorded_hashes:
        reasons.append("chybí evidence artifact hashes")
    else:
        for relative, expected in recorded_hashes.items():
            path = project_root / str(relative)
            if not path.is_file():
                reasons.append(f"evidence byla odstraněna: {relative}")
            elif _file_sha256(path) != str(expected):
                reasons.append(f"evidence se od review změnila: {relative}")

    if evidence.missing:
        reasons.append("aktuálně chybí povinná evidence")

    if status == "conditional":
        condition = decision.get("condition") or {}
        items = condition.get("items") or [] if isinstance(condition, dict) else []
        if not items:
            reasons.append("conditional rozhodnutí nemá podmínky")
        if not isinstance(condition, dict) or not str(condition.get("owner") or "").strip():
            reasons.append("conditional rozhodnutí nemá ownera podmínky")
        if not isinstance(condition, dict) or not str(condition.get("due_at") or "").strip():
            reasons.append("conditional rozhodnutí nemá termín")

    return DecisionValidation(valid=not reasons, reasons=reasons)


def generate_status(project_root: Path, platform_root: Path) -> dict[str, Any]:
    _, gates_cfg, journey = load_config(platform_root)
    workflow = _read_workflow(project_root)
    gate_states: list[dict[str, Any]] = []
    next_gate = None
    for gate in GATES:
        cfg = gates_cfg.get(gate) or {}
        evidence = evaluate_gate(project_root, gate, cfg)
        record = _load_gate_record(project_root, gate, cfg)
        gate_data = record.get("gate") or {}
        decision = str(gate_data.get("status") or "")
        validation = validate_gate_decision(project_root, gate, gate_data, evidence) if decision in HUMAN_DECISION_OUTCOMES else DecisionValidation(False, [])

        if decision == "passed" and validation.valid:
            effective = "passed"
        elif decision in {"conditional", "rejected"} and validation.valid:
            effective = decision
        else:
            effective = evidence.status

        if next_gate is None and effective != "passed":
            next_gate = gate
        decision_record = gate_data.get("decision") if isinstance(gate_data.get("decision"), dict) else {}
        gate_states.append(
            {
                "gate": gate,
                "stage": cfg.get("stage") or STAGES[int(gate[1:]) - 1],
                "status": effective,
                "present": evidence.present,
                "missing": evidence.missing,
                "question": cfg.get("question", ""),
                "decision_owner": decision_record.get("decision_owner"),
                "reviewer": decision_record.get("reviewer"),
                "approver": decision_record.get("approver"),
                "reviewed_at": decision_record.get("decided_at"),
                "conditions": list(gate_data.get("conditions") or []),
                "decision_valid": validation.valid if decision in HUMAN_DECISION_OUTCOMES else None,
                "decision_invalid_reasons": validation.reasons,
            }
        )
    if next_gate is None:
        next_gate = "G8"
    current_stage = STAGES[int(next_gate[1:]) - 1]
    recommendations = (journey.get("journey") or {}).get("actions") or {}
    action_cfg = recommendations.get(next_gate) or {}
    next_actions = action_cfg.get("actions") or ["Zkontroluj gate evidence a otevřené otázky."]
    prompt = action_cfg.get("prompt") or "Zobraz current status, chybějící evidence a navrhni nejmenší další krok."

    manifest = _project_manifest(project_root)
    owners = manifest.get("owners") or {}
    current_gate_state = next((item for item in gate_states if item["gate"] == next_gate), gate_states[0])
    blocker_lines = list(current_gate_state.get("missing") or [])
    decision_owner = str(owners.get("business_owner") or owners.get("architecture_owner") or "NEURČENO")
    project_commit = subprocess.run(
        ["git", "-C", str(project_root), "rev-parse", "HEAD"],
        check=False, capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).stdout.strip() or "UNCOMMITTED"
    status_description = "\n".join([
        f"Aktuální fáze: {current_stage}",
        f"Aktuální gate: {next_gate}",
        f"Gate status: {current_gate_state.get('status')}",
        f"Decision question: {current_gate_state.get('question')}",
        f"Decision owner: {current_gate_state.get('decision_owner') or decision_owner}",
        f"Reviewer: {current_gate_state.get('reviewer') or 'PENDING'}",
        f"Approver: {current_gate_state.get('approver') or 'PENDING'}",
        "Blocking evidence: " + (", ".join(blocker_lines) if blocker_lines else "žádné mechanické blokery"),
        "Open questions: " + (", ".join(current_gate_state.get('decision_invalid_reasons') or []) or "žádné evidované"),
        f"Project commit: {project_commit}",
        "Miro je projekce; gate schvaluje pouze člověk v Git decision recordu.",
    ])

    status_doc = _managed_artifact(
        "ddda.current-status",
        "project-status",
        "Current status",
        status_description,
        current_stage if current_stage in STAGES else "align",
        status="candidate",
        generated_at=now_utc(),
        current_stage=current_stage,
        next_gate=next_gate,
        current_gate_status=current_gate_state.get("status"),
        decision_question=current_gate_state.get("question"),
        decision_owner=current_gate_state.get("decision_owner") or decision_owner,
        reviewer=current_gate_state.get("reviewer"),
        approver=current_gate_state.get("approver"),
        reviewed_at=current_gate_state.get("reviewed_at"),
        open_questions=current_gate_state.get("decision_invalid_reasons") or [],
        blocking_evidence=blocker_lines,
        project_commit=project_commit,
        gates=gate_states,
        miro={
            "item_type": "sticky_note",
            "frame_id": "control-center",
            "position": {"x": 0, "y": 450, "origin": "center"},
            "geometry": {"width": 1200},
            "style": {"fillColor": "light_blue"},
        },
    )
    next_doc = _managed_artifact(
        "ddda.next-actions",
        "next-actions",
        "Doporučené další kroky",
        "; ".join(next_actions),
        current_stage if current_stage in STAGES else "align",
        status="candidate",
        generated_at=now_utc(),
        gate=next_gate,
        actions=next_actions,
        chat_prompt=prompt,
        mode_guidance=action_cfg.get("mode_guidance") or {"consult": "Plan", "execute": "Agent"},
        miro={
            "item_type": "sticky_note",
            "frame_id": "control-center",
            "position": {"x": 1300, "y": 450, "origin": "center"},
            "geometry": {"width": 1200},
            "style": {"fillColor": "light_green"},
        },
    )
    dump_yaml(status_doc, project_root / "artifacts" / "status" / "current-status.yaml")
    dump_yaml(next_doc, project_root / "artifacts" / "status" / "next-actions.yaml")
    report = {
        "project_root": str(project_root),
        "current_stage": current_stage,
        "next_gate": next_gate,
        "gates": gate_states,
        "next_actions": next_actions,
        "chat_prompt": prompt,
    }
    dump_yaml({"status_report": report}, project_root / "reports" / "project-status.yaml")
    return report


def review_gate(
    project_root: Path,
    platform_root: Path,
    gate: str,
    outcome: str,
    reviewer: str,
    note: str | None,
    conditions: Iterable[str],
    *,
    decision_owner: str,
    approver: str,
    scope: str,
    provenance: str = "human",
    condition_owner: str | None = None,
    condition_due_at: str | None = None,
    test_simulation: bool = False,
) -> dict[str, Any]:
    if gate not in GATES:
        raise SteeringError(f"Neznámá gate: {gate}")
    if outcome not in HUMAN_DECISION_OUTCOMES:
        raise SteeringError(f"Nepodporovaný outcome: {outcome}")

    _assert_clean_project(project_root)
    project_commit = _git_head(project_root)
    if test_simulation:
        if not _is_test_fixture(project_root):
            raise SteeringError("Testovací gate simulation je povolena pouze v označeném dočasném test fixture projektu.")
        provenance = "test_simulation"
    elif provenance != "human":
        raise SteeringError("Produkční gate rozhodnutí musí mít provenance=human.")

    reviewer_value = reviewer if provenance == "test_simulation" else _human_identity(reviewer, "gate_decision.reviewer")
    approver_value = approver if provenance == "test_simulation" else _human_identity(approver, "gate_decision.approver")
    owner_value = decision_owner if provenance == "test_simulation" else _decision_owner(project_root, decision_owner)
    scope_value = _required_text(scope, "gate_decision.scope")

    condition_items = [str(item).strip() for item in conditions if str(item).strip()]
    if outcome == "passed" and condition_items:
        raise SteeringError("passed rozhodnutí nesmí obsahovat neuzavřené podmínky.")
    if outcome == "conditional":
        if not condition_items:
            raise SteeringError("conditional rozhodnutí vyžaduje alespoň jednu podmínku.")
        _required_text(condition_owner, "gate_decision.condition.owner")
        _required_text(condition_due_at, "gate_decision.condition.due_at")

    _, gates_cfg, _ = load_config(platform_root)
    cfg = gates_cfg.get(gate) or {}
    evidence = evaluate_gate(project_root, gate, cfg)
    if outcome == "passed" and evidence.missing:
        raise SteeringError(f"Gate {gate} nelze schválit; chybí evidence: {', '.join(evidence.missing)}")

    decision = {
        "gate": gate,
        "outcome": outcome,
        "project_id": _project_id(project_root),
        "scope": scope_value,
        "evidence": {
            "project_commit": project_commit,
            "scope_sha256": _project_scope_hash(project_root),
            "artifact_hashes": _artifact_hashes(project_root, evidence.present),
        },
        "decision_owner": owner_value,
        "reviewer": reviewer_value,
        "approver": approver_value,
        "decided_at": now_utc(),
        "provenance": provenance,
        "condition": {
            "items": condition_items,
            "owner": condition_owner,
            "due_at": condition_due_at,
        } if outcome == "conditional" else None,
    }

    path = project_root / "decisions" / "gates" / f"{gate}.yaml"
    record = _load_gate_record(project_root, gate, cfg)
    gate_data = record.setdefault("gate", {})
    history = list(gate_data.get("decision_history") or [])
    previous = gate_data.get("decision")
    if isinstance(previous, dict):
        archived = copy.deepcopy(previous)
        archived["superseded_at"] = now_utc()
        history.append(archived)
    gate_data["status"] = outcome
    gate_data["evidence"] = {"present": evidence.present, "missing": evidence.missing, "disputed": gate_data.get("evidence", {}).get("disputed", [])}
    gate_data["conditions"] = condition_items
    gate_data["decision"] = decision
    gate_data["decision_history"] = history
    gate_data["reviewed_at"] = decision["decided_at"]
    gate_data["reviewed_by"] = reviewer_value
    gate_data["note"] = note
    dump_yaml(record, path)

    manifest_path = project_root / "project.yaml"
    with manifest_path.open("r", encoding="utf-8-sig") as handle:
        manifest = YAML_RT.load(handle)
    workflow = manifest.setdefault("workflow", {})
    completed = [item for item in list(workflow.get("completed_gates") or []) if item != gate]
    if outcome == "passed":
        completed.append(gate)
        completed.sort(key=lambda item: int(item[1:]))
        workflow["current_stage"] = NEXT_STAGE[gate]
    workflow["completed_gates"] = completed
    with manifest_path.open("w", encoding="utf-8", newline="\n") as handle:
        YAML_RT.dump(manifest, handle)
    return generate_status(project_root, platform_root)


def validate_agent_contract(project_root: Path) -> dict[str, Any]:
    path = project_root / ".ddda" / "agent-contract.yaml"
    doc = load_yaml(path)
    contract = doc.get("agent_contract") if isinstance(doc, dict) else None
    required = ["id", "name", "role", "inputs", "outputs", "allowed_write_paths", "forbidden_actions", "validation", "handoff_rules", "downstream_consumers"]
    missing = [key for key in required if not isinstance(contract, dict) or key not in contract]
    return {"status": "ok" if not missing else "invalid", "missing": missing, "path": str(path)}


def json_text(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)

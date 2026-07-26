from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import jsonschema
from ruamel.yaml import YAML

TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".ps1",
    ".py",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".xml",
    ".csv",
    ".mmd",
    ".cml",
}


def load_yaml(path: Path) -> Any:
    yaml = YAML(typ="safe")
    with path.open("r", encoding="utf-8-sig") as handle:
        return yaml.load(handle)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def validate_lint(root: Path) -> list[str]:
    failures: list[str] = []

    root_docs = sorted(path.name for path in (root / "docs").glob("*.md"))
    if root_docs != ["README.md"]:
        failures.append(f"docs root must contain only README.md, found: {root_docs}")

    knowledge_files = sorted(path.name for path in (root / "knowledge").glob("*.md"))
    for index in range(13):
        prefix = f"{index:02d}-"
        if not any(name.startswith(prefix) for name in knowledge_files):
            failures.append(f"knowledge pack missing prefix {prefix}")

    forbidden_generated = (
        ".tmp",
        ".reports",
        ".releases",
        "dist",
        "__pycache__",
        ".pytest_cache",
    )
    for path in root.rglob("*"):
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        parts = relative.parts
        if any(part in forbidden_generated for part in parts):
            failures.append(f"generated or local-state path is present in repository: {relative.as_posix()}")

    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        if any(part == ".git" for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if "\t" in text:
            failures.append(f"tab character found: {path.relative_to(root).as_posix()}")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if line.rstrip(" \t") != line:
                failures.append(
                    f"trailing whitespace: {path.relative_to(root).as_posix()}:{line_number}"
                )

    return failures


def validate_schema(root: Path) -> list[str]:
    failures: list[str] = []
    schemas: dict[str, Any] = {}
    for path in sorted((root / "schemas").glob("*.json")):
        try:
            schemas[path.name] = load_json(path)
        except Exception as exc:  # pragma: no cover - diagnostics
            failures.append(f"invalid JSON schema {path}: {exc}")

    yaml_paths: list[Path] = []
    for relative_root in (
        "templates",
        "scaffolds",
        "examples",
        "config",
        "docs/reference",
    ):
        current = root / relative_root
        if current.exists():
            yaml_paths.extend(current.rglob("*.yaml"))
            yaml_paths.extend(current.rglob("*.yml"))

    parsed: dict[str, Any] = {}
    for path in sorted(set(yaml_paths)):
        try:
            parsed[path.relative_to(root).as_posix()] = load_yaml(path)
        except Exception as exc:  # pragma: no cover - diagnostics
            failures.append(f"invalid YAML {path.relative_to(root).as_posix()}: {exc}")

    validations = [
        (
            "examples/life-insurance-greenfield/project.yaml",
            "project.schema.json",
        ),
        (
            "scaffolds/miro/strategic-ddd-method-board.yaml",
            "miro-scaffold.schema.json",
        ),
        (
            "templates/project/project-intake.template.yaml",
            "project-intake.schema.json",
        ),
        (
            "docs/reference/capability-catalog.yaml",
            "capability-catalog.schema.json",
        ),
        (
            "examples/minimal/manifest.yaml",
            "ingestion-manifest.schema.json",
        ),
        (
            "examples/minimal/expected-invariants.yaml",
            None,
        ),
    ]

    for document_path, schema_name in validations:
        if document_path not in parsed:
            failures.append(f"missing parsed document: {document_path}")
            continue
        if schema_name is None:
            continue
        if schema_name not in schemas:
            failures.append(f"missing schema: {schema_name}")
            continue
        try:
            jsonschema.validate(parsed[document_path], schemas[schema_name])
        except Exception as exc:
            failures.append(f"schema validation failed for {document_path}: {exc}")

    catalog = parsed.get("docs/reference/capability-catalog.yaml")
    if isinstance(catalog, dict):
        for capability in catalog.get("capabilities", []):
            capability_id = capability.get("id", "unknown")
            for value in (
                list(capability.get("documentation", []))
                + list(capability.get("commands", []))
                + list(capability.get("tests", []))
            ):
                path = root / value
                if value.endswith("/tests"):
                    if not path.is_dir():
                        failures.append(f"{capability_id}: missing directory {value}")
                elif not path.exists():
                    failures.append(f"{capability_id}: missing referenced path {value}")

    managed_schema = schemas.get("managed-artifact.schema.json")
    if managed_schema is not None:
        artifact_root = root / "examples/life-insurance-greenfield/artifacts"
        if artifact_root.exists():
            for path in artifact_root.rglob("*.yaml"):
                try:
                    document = load_yaml(path)
                    if isinstance(document, dict) and "artifact" in document:
                        jsonschema.validate(document, managed_schema)
                except Exception as exc:
                    failures.append(
                        f"managed artifact validation failed for {path.relative_to(root).as_posix()}: {exc}"
                    )

    return failures


def validate_security(root: Path) -> list[str]:
    failures: list[str] = []
    windows_user_path = re.compile(r"(?i)[A-Z]:\\Users\\[^\\\s]+\\")
    unix_user_path = re.compile(r"(?i)/(Users|home)/[^/\s]+/")
    literal_secret = re.compile(
        r"(?i)MIRO_ACCESS_TOKEN\s*[:=]\s*['\"][A-Za-z0-9._-]{20,}['\"]"
    )

    checked_roots = (
        root / "scripts",
        root / "templates",
        root / "examples",
        root / "config",
        root / "knowledge",
        root / "runtime",
    )
    for checked_root in checked_roots:
        if not checked_root.exists():
            continue
        for path in checked_root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            relative = path.relative_to(root).as_posix()
            if windows_user_path.search(text):
                failures.append(f"user-specific Windows path found: {relative}")
            if unix_user_path.search(text):
                failures.append(f"user-specific Unix path found: {relative}")
            if literal_secret.search(text):
                failures.append(f"probable literal Miro secret found: {relative}")

    forbidden_names = {
        ".env",
        "miro-access-token.xml",
        "credentials.json",
        "secrets.json",
    }
    for path in root.rglob("*"):
        if path.is_file() and path.name.lower() in forbidden_names:
            failures.append(f"forbidden secret-like file found: {path.relative_to(root).as_posix()}")

    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument(
        "--suite",
        choices=("lint", "schema", "security", "all"),
        default="all",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        raise SystemExit(f"Repository root does not exist: {root}")

    failures: list[str] = []
    if args.suite in ("lint", "all"):
        failures.extend(validate_lint(root))
    if args.suite in ("schema", "all"):
        failures.extend(validate_schema(root))
    if args.suite in ("security", "all"):
        failures.extend(validate_security(root))

    result = {
        "suite": args.suite,
        "status": "PASS" if not failures else "FAIL",
        "failure_count": len(failures),
        "failures": failures,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        for failure in failures:
            print(f"[FAIL] {failure}")
        print(f"DDDA repository {args.suite} validation: {result['status']}")

    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

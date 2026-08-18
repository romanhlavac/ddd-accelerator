from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
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

LOCAL_STATE_PARTS = {".git", ".ddda"}
FORBIDDEN_DISTRIBUTED_PARTS = {
    ".tmp",
    ".reports",
    ".releases",
    "dist",
    "__pycache__",
    ".pytest_cache",
}


CANONICAL_GITHUB_AUTH_MARKERS = (
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "gh auth token",
    "git credential helper",
)

RELEASE_CONTRACT_DOCUMENTS = (
    "CHANGELOG.md",
    "docs/user-guide/validate-and-promote-pr.md",
    "docs/developer-guide/platform-development-lifecycle.md",
    "docs/reference/cli.md",
)

FORBIDDEN_GITHUB_CLI_REQUIREMENT_PHRASES = (
    "promotion vyžaduje github cli",
    "promote-pr vyžaduje github cli",
    "github cli je povinn",
    "requires github cli",
    "github cli is required",
)

SEMVER_PATTERN = r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?"
RELEASE_HEADING_PATTERN = re.compile(
    rf"^## \[(?P<version>{SEMVER_PATTERN})\] - (?P<date>[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}})\s*$",
    re.MULTILINE,
)
UNRELEASED_HEADING_PATTERN = re.compile(r"^## \[Unreleased\]\s*$", re.MULTILINE)
RELEASE_ITEM_PATTERN = re.compile(r"^\s*(?:[-*+]\s+|[0-9]+\.\s+)", re.MULTILINE)


def load_yaml(path: Path) -> Any:
    yaml = YAML(typ="safe")
    with path.open("r", encoding="utf-8-sig") as handle:
        return yaml.load(handle)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def tracked_or_distributed_files(root: Path) -> list[Path]:
    git_dir = root / ".git"
    if git_dir.exists():
        process = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=False,
            capture_output=True,
        )
        if process.returncode == 0:
            return [
                root / value.decode("utf-8", errors="strict")
                for value in process.stdout.split(b"\0")
                if value
            ]

    return [
        path
        for path in root.rglob("*")
        if path.is_file() and not any(part in LOCAL_STATE_PARTS for part in path.relative_to(root).parts)
    ]


def _section_body(text: str, heading_match: re.Match[str]) -> str:
    start = heading_match.end()
    next_heading = re.search(r"^##\s+", text[start:], re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end]


def validate_release_contracts(root: Path) -> list[str]:
    failures: list[str] = []

    documentation_paths = [root / "README.md", root / "USAGE.md", root / "CHANGELOG.md"]
    docs_root = root / "docs"
    if docs_root.exists():
        documentation_paths.extend(sorted(docs_root.rglob("*.md")))

    for path in documentation_paths:
        if not path.exists():
            continue
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        folded = text.casefold()
        for phrase in FORBIDDEN_GITHUB_CLI_REQUIREMENT_PHRASES:
            if phrase in folded:
                failures.append(
                    f"documentation claims GitHub CLI is required: {relative}: {phrase}"
                )
        if re.search(
            r"(?im)^\s*[^\n]*promote-pr[^\n]*\s-(?:token|githubtoken)\b",
            text,
        ):
            failures.append(
                f"documentation exposes a token CLI argument for promote-pr: {relative}"
            )

    implementation_path = root / "scripts/platform/DDDAGitHubSupport.ps1"
    if not implementation_path.exists():
        failures.append("missing GitHub authentication implementation: scripts/platform/DDDAGitHubSupport.ps1")
    else:
        implementation = implementation_path.read_text(
            encoding="utf-8-sig", errors="replace"
        ).casefold()
        positions = [implementation.find(marker.casefold()) for marker in CANONICAL_GITHUB_AUTH_MARKERS]
        if any(position < 0 for position in positions):
            missing = [
                marker
                for marker, position in zip(CANONICAL_GITHUB_AUTH_MARKERS, positions)
                if position < 0
            ]
            failures.append(
                "GitHub authentication implementation is missing providers: "
                + ", ".join(missing)
            )
        elif positions != sorted(positions):
            failures.append(
                "GitHub authentication provider order must be GH_TOKEN, GITHUB_TOKEN, gh auth token, git credential helper"
            )

    for relative in RELEASE_CONTRACT_DOCUMENTS:
        path = root / relative
        if not path.exists():
            failures.append(f"missing release contract document: {relative}")
            continue
        folded = path.read_text(encoding="utf-8-sig", errors="replace").casefold()
        positions = [folded.find(marker.casefold()) for marker in CANONICAL_GITHUB_AUTH_MARKERS]
        if any(position < 0 for position in positions):
            missing = [
                marker
                for marker, position in zip(CANONICAL_GITHUB_AUTH_MARKERS, positions)
                if position < 0
            ]
            failures.append(
                f"release contract document missing GitHub auth providers: {relative}: {', '.join(missing)}"
            )
        elif positions != sorted(positions):
            failures.append(
                f"release contract document has inconsistent GitHub auth provider order: {relative}"
            )

    changelog_path = root / "CHANGELOG.md"
    if not changelog_path.exists():
        failures.append("missing changelog: CHANGELOG.md")
        return failures

    changelog = changelog_path.read_text(encoding="utf-8-sig", errors="replace")
    unreleased_matches = list(UNRELEASED_HEADING_PATTERN.finditer(changelog))
    if len(unreleased_matches) != 1:
        failures.append(
            f"CHANGELOG.md must contain exactly one '## [Unreleased]' heading, found {len(unreleased_matches)}"
        )
    # Development changes intentionally live under Unreleased. Requiring that
    # section to be empty belongs to promotion-time Assert-DDDAPlatformChangelogRelease,
    # not ordinary PR/source repository validation.

    release_matches = list(RELEASE_HEADING_PATTERN.finditer(changelog))
    if not release_matches:
        failures.append("CHANGELOG.md contains no versioned release heading")
        return failures

    versions: set[str] = set()
    for match in release_matches:
        version = match.group("version")
        date_text = match.group("date")
        if version in versions:
            failures.append(f"CHANGELOG.md contains duplicate release version: {version}")
        versions.add(version)
        try:
            parsed = dt.date.fromisoformat(date_text)
        except ValueError:
            failures.append(
                f"CHANGELOG.md release {version} has invalid ISO date: {date_text}"
            )
        else:
            if parsed.isoformat() != date_text:
                failures.append(
                    f"CHANGELOG.md release {version} has non-canonical ISO date: {date_text}"
                )
        if not RELEASE_ITEM_PATTERN.search(_section_body(changelog, match)):
            failures.append(
                f"CHANGELOG.md release {version} contains no release items"
            )

    if unreleased_matches and release_matches:
        if unreleased_matches[0].start() > release_matches[0].start():
            failures.append("CHANGELOG.md [Unreleased] must precede versioned releases")

    promotion_path = root / "scripts/platform/Invoke-DDDAPromotePr.ps1"
    promotion_support_path = root / "scripts/platform/DDDAPlatformSupport.ps1"
    for path, required in (
        (promotion_path, "Assert-DDDAPlatformChangelogRelease"),
        (promotion_support_path, "function Assert-DDDAPlatformChangelogRelease"),
    ):
        if not path.exists():
            failures.append(f"missing release preflight implementation: {path.relative_to(root).as_posix()}")
        elif required not in path.read_text(encoding="utf-8-sig", errors="replace"):
            failures.append(
                f"release preflight does not enforce changelog/version contract: {path.relative_to(root).as_posix()}"
            )

    return failures


def validate_lint(root: Path) -> list[str]:
    failures: list[str] = []

    if (root / "CHANGELOG.md").exists() or (root / "scripts/platform/DDDAGitHubSupport.ps1").exists():
        failures.extend(validate_release_contracts(root))

    root_docs = sorted(path.name for path in (root / "docs").glob("*.md"))
    if root_docs != ["README.md"]:
        failures.append(f"docs root must contain only README.md, found: {root_docs}")

    knowledge_files = sorted(path.name for path in (root / "knowledge").glob("*.md"))
    for index in range(13):
        prefix = f"{index:02d}-"
        if not any(name.startswith(prefix) for name in knowledge_files):
            failures.append(f"knowledge pack missing prefix {prefix}")

    files = tracked_or_distributed_files(root)
    for path in files:
        relative = path.relative_to(root)
        if any(part in FORBIDDEN_DISTRIBUTED_PARTS for part in relative.parts):
            failures.append(
                f"generated or local-state path is tracked or distributed: {relative.as_posix()}"
            )

    for path in files:
        if not path.exists() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        relative = path.relative_to(root)
        if any(part in LOCAL_STATE_PARTS for part in relative.parts):
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if "\t" in text:
            failures.append(f"tab character found: {relative.as_posix()}")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if line.rstrip(" \t") != line:
                failures.append(f"trailing whitespace: {relative.as_posix()}:{line_number}")

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
        ("examples/life-insurance-greenfield/project.yaml", "project.schema.json"),
        ("scaffolds/miro/strategic-ddd-method-board.yaml", "miro-scaffold.schema.json"),
        ("templates/project/project-intake.template.yaml", "project-intake.schema.json"),
        ("docs/reference/capability-catalog.yaml", "capability-catalog.schema.json"),
        ("examples/minimal/manifest.yaml", "ingestion-manifest.schema.json"),
        ("examples/minimal/expected-invariants.yaml", None),
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
            relative_path = path.relative_to(root)
            if any(part in LOCAL_STATE_PARTS for part in relative_path.parts):
                continue
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            relative = relative_path.as_posix()
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
    for path in tracked_or_distributed_files(root):
        if path.name.lower() in forbidden_names:
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

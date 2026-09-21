import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AUTH_SCRIPT = ROOT / "scripts" / "platform" / "Test-DDDAControlledPromotionAuthorization.py"
WORKFLOW = ROOT / ".github" / "workflows" / "controlled-release-candidate-promotion.yml"
SPEC = importlib.util.spec_from_file_location("controlled_promotion_authorization", AUTH_SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

REPOSITORY = "romanhlavac/ddd-accelerator"
PR = 146
SOURCE_SHA = "4" * 40
VERSION = "0.1.1"
PACKAGE_SHA = "7" * 64
ACTOR = "romanhlavac"
COMMAND = (
    f"/ddda promote-controlled --source-sha {SOURCE_SHA} "
    f"--version {VERSION} --package-sha256 {PACKAGE_SHA}"
)


def authorization_comment(**overrides):
    body = f'''<!-- ddda:promotion-release-authorization:v1 -->
```json
{{
  "schema_version": 1,
  "repository": "{REPOSITORY}",
  "pr": {PR},
  "source_sha": "{SOURCE_SHA}",
  "candidate_package_sha256": "{PACKAGE_SHA}",
  "version": "{VERSION}",
  "authorizer": "{ACTOR}",
  "decision": "approve",
  "authorized_command": "promote-pr -Pr {PR} -Version {VERSION} -ConfirmPromotion",
  "release_source_mode": "CONTROLLED_EXACT_PR_SHA",
  "candidate_merge_allowed": false,
  "authorized_side_effects_after_canonical_pass": [
    "release_package",
    "release_validation",
    "tag:v{VERSION}",
    "github_release:v{VERSION}"
  ]
}}
```
'''
    value = {
        "id": 123,
        "issue_url": f"https://api.github.com/repos/{REPOSITORY}/issues/{PR}",
        "body": body,
        "user": {"login": ACTOR, "type": "User"},
    }
    value.update(overrides)
    return value


def validate(comments, command=COMMAND, actor=ACTOR):
    return MODULE.validate_authorization(
        comments,
        repository=REPOSITORY,
        pr_number=PR,
        actor=actor,
        command_text=command,
    )


def test_exact_human_authorization_is_accepted():
    result = validate([[authorization_comment()]])
    assert result["status"] == "PASS"
    assert result["authorization_comment_id"] == 123
    assert result["source_sha"] == SOURCE_SHA
    assert result["candidate_package_sha256"] == PACKAGE_SHA


def test_multiple_authorization_markers_fail_closed():
    result = validate([[authorization_comment(), authorization_comment(id=124)]])
    assert result["status"] == "FAIL"
    assert "CONTROLLED_PROMOTION_AUTHORIZATION_MARKER_COUNT_INVALID" in result["failures"]


def test_bot_or_different_actor_cannot_authorize_promotion():
    bot = authorization_comment(user={"login": "release-bot[bot]", "type": "Bot"})
    result = validate([[bot]], actor="release-bot[bot]")
    assert result["status"] == "FAIL"
    assert "CONTROLLED_PROMOTION_AUTHORIZATION_PROVENANCE_INVALID" in result["failures"]


def test_command_identity_must_match_authorized_release_identity():
    wrong_command = COMMAND.replace(PACKAGE_SHA, "8" * 64)
    result = validate([[authorization_comment()]], command=wrong_command)
    assert result["status"] == "FAIL"
    assert "CONTROLLED_PROMOTION_AUTHORIZATION_PACKAGE_MISMATCH" in result["failures"]


def test_production_workflow_is_human_comment_triggered_and_write_scoped():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "issue_comment:" in text
    assert "startsWith(github.event.comment.body, '/ddda promote-controlled ')" in text
    assert "environment: ddda-backlog-governance" in text
    assert "contents: write" in text
    assert "DDDA_GITHUB_PROJECT_TOKEN" in text
    assert "Checkout trusted default-branch control plane" in text
    assert "Trusted control plane is stale." in text


def test_production_workflow_binds_authorization_candidate_and_hrdr_artifact():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "Test-DDDAControlledPromotionAuthorization.py" in text
    assert "Test-DDDAControlledReleaseCandidate.py" in text
    assert "--operation promotion_dry_run" in text
    assert "Read exact Human Release Decision Record" in text
    assert "$validationRun = [long]$hrdr.evidence.validation_workflow_run" in text
    assert 'actions/runs/$validationRun/artifacts?per_page=100' in text
    assert "HRDR-bound validation report package hash does not match the explicit release authorization." in text


def test_production_workflow_requires_fresh_dry_run_before_confirmed_promotion():
    text = WORKFLOW.read_text(encoding="utf-8")

    dry_run = text.index("      - name: Run governed promotion dry-run immediately before release")
    verify = text.index("      - name: Verify dry-run PASS and zero-side-effect evidence")
    fresh = text.index("      - name: Fresh read-back before irreversible side effects")
    confirm = text.index("      - name: Execute canonical controlled promotion")
    post = text.index("      - name: Fresh post-release read-back")

    assert dry_run < verify < fresh < confirm < post
    dry_run_block = text[dry_run:verify]
    confirm_block = text[confirm:post]
    assert "-DryRun" in dry_run_block
    assert "-ConfirmPromotion" in confirm_block
    assert "-ConfirmMerge" not in text
    assert "gh auth setup-git" in text


def test_post_release_readback_proves_no_candidate_merge_and_canonical_publication():
    text = WORKFLOW.read_text(encoding="utf-8")
    post = text.split("      - name: Fresh post-release read-back", 1)[1]

    assert "Controlled release source PR was merged, closed, or drifted." in post
    assert "Controlled promotion changed the default branch; this is forbidden." in post
    assert "Canonical tag target" in post
    assert "releases/tags/$tag" in post
    assert "Canonical GitHub Release read-back is invalid." in post
    assert "result.json" in post
    assert "result.md" in post
    assert "controlled-candidate-promotion-${{ env.CANDIDATE_PR }}-${{ env.SOURCE_SHA }}" in post

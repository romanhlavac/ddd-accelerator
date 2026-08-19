from pathlib import Path
import os
import subprocess

ROOT = Path(__file__).resolve().parents[3]
PROMOTION = ROOT / "scripts" / "platform" / "Invoke-DDDAPromotePr.ps1"
RECOVERY_DOC = ROOT / "docs" / "developer-guide" / "release-tag-recovery.md"


def _run(args, *, env, check=True):
    return subprocess.run(args, env=env, text=True, capture_output=True, check=check)


def test_release_executor_configures_deterministic_repo_local_tagger_before_tag_creation():
    text = PROMOTION.read_text(encoding="utf-8-sig")

    name_assignment = '$releaseTaggerName = "DDDA Release Tagger"'
    email_assignment = '$releaseTaggerEmail = "ddda-release-tagger@example.invalid"'
    name_config = '@("config", "user.name", $releaseTaggerName)'
    email_config = '@("config", "user.email", $releaseTaggerEmail)'
    tag_creation = '@("tag", "-a", $tag, $mergeCommit, "-m", "DDDA $Version")'

    for contract in (name_assignment, email_assignment, name_config, email_config, tag_creation):
        assert contract in text

    assert text.index(name_assignment) < text.index(tag_creation)
    assert text.index(email_assignment) < text.index(tag_creation)
    assert text.index(name_config) < text.index(tag_creation)
    assert text.index(email_config) < text.index(tag_creation)
    assert '@("push", "origin", $tag)' in text


def test_annotated_release_tag_succeeds_without_ambient_git_identity(tmp_path):
    repo = tmp_path / "repo"
    empty_global = tmp_path / "empty.gitconfig"
    empty_global.write_text("", encoding="utf-8")

    clean_env = os.environ.copy()
    clean_env["GIT_CONFIG_GLOBAL"] = str(empty_global)
    clean_env["GIT_CONFIG_NOSYSTEM"] = "1"
    for key in (
        "GIT_AUTHOR_NAME",
        "GIT_AUTHOR_EMAIL",
        "GIT_COMMITTER_NAME",
        "GIT_COMMITTER_EMAIL",
    ):
        clean_env.pop(key, None)

    _run(["git", "init", "-b", "main", str(repo)], env=clean_env)
    (repo / "fixture.txt").write_text("fixture\n", encoding="utf-8")
    _run(["git", "-C", str(repo), "add", "."], env=clean_env)
    _run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Fixture Committer",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-m",
            "fixture",
        ],
        env=clean_env,
    )
    commit = _run(["git", "-C", str(repo), "rev-parse", "HEAD"], env=clean_env).stdout.strip()

    assert _run(["git", "-C", str(repo), "config", "--get", "user.name"], env=clean_env, check=False).returncode == 1
    assert _run(["git", "-C", str(repo), "config", "--get", "user.email"], env=clean_env, check=False).returncode == 1

    _run(["git", "-C", str(repo), "config", "user.name", "DDDA Release Tagger"], env=clean_env)
    _run(["git", "-C", str(repo), "config", "user.email", "ddda-release-tagger@example.invalid"], env=clean_env)
    _run(["git", "-C", str(repo), "tag", "-a", "v9.9.9", commit, "-m", "DDDA 9.9.9"], env=clean_env)

    target = _run(["git", "-C", str(repo), "rev-list", "-n", "1", "v9.9.9"], env=clean_env).stdout.strip()
    record = _run(
        [
            "git",
            "-C",
            str(repo),
            "for-each-ref",
            "refs/tags/v9.9.9",
            "--format=%(taggername)|%(taggeremail)|%(contents)",
        ],
        env=clean_env,
    ).stdout.strip()

    assert target == commit
    assert record == "DDDA Release Tagger|<ddda-release-tagger@example.invalid>|DDDA 9.9.9"


def test_release_tag_recovery_runbook_is_bounded():
    text = RECOVERY_DOC.read_text(encoding="utf-8")
    for invariant in (
        "same version",
        "same validated release SHA",
        "same release report",
        "same release package SHA-256",
        "separate explicit human recovery authorization",
        "existing canonical tag",
        "no history rewrite",
    ):
        assert invariant in text

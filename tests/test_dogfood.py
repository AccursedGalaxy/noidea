"""Tests for the agent-backend dogfood loop: queue → seed → reconcile, and the match gates.

These pin the edge cases worked out in the design grill: git-cleanup-aware normalization, the
accepted/modified split with no tuned floor, the path-overlap + TTL seeding gates, the seed
pointer lifecycle, and the reconcile verdict (including expiry → discarded).
"""

from unittest.mock import patch

from noidea.dogfood import (
    ACCEPTED,
    DISCARDED,
    MODIFIED,
    classify,
    clear_seeded,
    find_fresh_proposal,
    mark_seeded,
    message_similarity,
    new_run_id,
    normalize_message,
    read_seeded,
    reconcile,
    record_proposal,
    run_file_for,
)

TTL = 3600


def _record(repo_root, run_id, branch, files, message, run_file, created_at):
    """Queue a proposal at a fixed time, bypassing the prune by using the same clock."""
    return record_proposal(
        repo_root, run_id, branch, files, message, run_file, TTL, now_unix=created_at
    )


# ---- normalization & similarity ----


def test_normalize_matches_git_cleanup():
    """git strips trailing whitespace and surrounding blank lines on commit, so an
    accepted-verbatim message must normalize equal to what git stored."""
    proposed = "feat: add thing   \n\n- did it  \n"
    committed = "\nfeat: add thing\n\n- did it"
    assert normalize_message(proposed) == normalize_message(committed)


def test_normalize_handles_crlf():
    assert normalize_message("a\r\nb\r\n") == "a\nb"


def test_similarity_identical_after_cleanup_is_one():
    assert message_similarity("feat: x  ", "feat: x") == 1.0


def test_similarity_different_is_between_zero_and_one():
    ratio = message_similarity("feat: add login", "chore: bump deps")
    assert 0.0 <= ratio < 1.0


def test_classify_accepted_vs_modified():
    assert classify("feat: x", "feat: x") == (ACCEPTED, 1.0)
    disposition, ratio = classify("feat: add login flow", "feat: add login")
    assert disposition == MODIFIED and 0.0 < ratio < 1.0


# ---- queue: find_fresh_proposal gates ----


def test_find_fresh_requires_path_overlap(tmp_path):
    """A queued proposal for one set of files must not seed an unrelated commit's buffer."""
    repo = str(tmp_path)
    _record(
        repo, "r1", "main", ["auth.py"], "feat: auth", "/x/r1.json", created_at=100.0
    )
    # Committing unrelated files: no overlap → no match (the grilled UX guard).
    assert find_fresh_proposal(repo, ["README.md"], "main", TTL, now_unix=200.0) is None
    # Overlapping files → match.
    found = find_fresh_proposal(repo, ["auth.py", "x.py"], "main", TTL, now_unix=200.0)
    assert found is not None and found.run_id == "r1"


def test_find_fresh_respects_branch(tmp_path):
    repo = str(tmp_path)
    _record(repo, "r1", "feat/login", ["a.py"], "m", "/x/r1.json", created_at=100.0)
    assert find_fresh_proposal(repo, ["a.py"], "main", TTL, now_unix=150.0) is None
    assert (
        find_fresh_proposal(repo, ["a.py"], "feat/login", TTL, now_unix=150.0)
        is not None
    )


def test_find_fresh_respects_ttl(tmp_path):
    repo = str(tmp_path)
    _record(repo, "r1", "main", ["a.py"], "m", "/x/r1.json", created_at=100.0)
    # Past the TTL window → expired, not eligible to seed.
    assert (
        find_fresh_proposal(repo, ["a.py"], "main", TTL, now_unix=100.0 + TTL + 1)
        is None
    )


def test_find_fresh_returns_newest(tmp_path):
    """Re-running --agent before committing queues a second proposal; the newest wins."""
    repo = str(tmp_path)
    _record(repo, "old", "main", ["a.py"], "old msg", "/x/old.json", created_at=100.0)
    _record(repo, "new", "main", ["a.py"], "new msg", "/x/new.json", created_at=200.0)
    found = find_fresh_proposal(repo, ["a.py"], "main", TTL, now_unix=300.0)
    assert found is not None and found.run_id == "new"


def test_consumed_proposal_is_not_found(tmp_path):
    """After reconcile tombstones a proposal, it is no longer eligible to seed."""
    repo = str(tmp_path)
    run_file = str(tmp_path / "r1.json")
    _record(repo, "r1", "main", ["a.py"], "feat: x", run_file, created_at=100.0)
    mark_seeded(repo, "r1", now_unix=110.0)
    with (
        patch("noidea.dogfood.get_commit_message", return_value="feat: x"),
        patch("noidea.dogfood.get_head_sha", return_value="abc123"),
    ):
        reconcile(repo, TTL, now_unix=120.0)
    assert find_fresh_proposal(repo, ["a.py"], "main", TTL, now_unix=130.0) is None


# ---- seed pointer lifecycle ----


def test_seed_pointer_roundtrip(tmp_path):
    repo = str(tmp_path)
    assert read_seeded(repo) is None
    mark_seeded(repo, "r1", now_unix=100.0)
    assert read_seeded(repo)["run_id"] == "r1"
    clear_seeded(repo)
    assert read_seeded(repo) is None


# ---- reconcile verdicts ----


def test_reconcile_accepted_when_committed_verbatim(tmp_path):
    repo = str(tmp_path)
    run_file = str(tmp_path / "r1.json")
    _record(repo, "r1", "main", ["a.py"], "feat: add x", run_file, created_at=100.0)
    mark_seeded(repo, "r1", now_unix=110.0)
    with (
        patch("noidea.dogfood.get_commit_message", return_value="feat: add x\n"),
        patch("noidea.dogfood.get_head_sha", return_value="sha1"),
    ):
        result = reconcile(repo, TTL, now_unix=120.0)
    assert (
        result is not None
        and result.disposition == ACCEPTED
        and result.similarity == 1.0
    )
    # The seed pointer is consumed so the next commit does not re-reconcile.
    assert read_seeded(repo) is None


def test_reconcile_modified_when_edited(tmp_path):
    repo = str(tmp_path)
    run_file = str(tmp_path / "r1.json")
    _record(
        repo, "r1", "main", ["a.py"], "feat: add login flow", run_file, created_at=100.0
    )
    mark_seeded(repo, "r1", now_unix=110.0)
    with (
        patch("noidea.dogfood.get_commit_message", return_value="feat: add login"),
        patch("noidea.dogfood.get_head_sha", return_value="sha1"),
    ):
        result = reconcile(repo, TTL, now_unix=120.0)
    assert (
        result is not None
        and result.disposition == MODIFIED
        and result.similarity < 1.0
    )


def test_reconcile_no_seed_is_noop(tmp_path):
    """A fast-path (or non-noidea) commit left no seed pointer → nothing to reconcile."""
    repo = str(tmp_path)
    with (
        patch("noidea.dogfood.get_commit_message", return_value="whatever"),
        patch("noidea.dogfood.get_head_sha", return_value="sha1"),
    ):
        assert reconcile(repo, TTL, now_unix=120.0) is None


def test_reconcile_writes_verdict_into_run_record(tmp_path):
    """The verdict is appended to the driver-os trace record, making it a labelled example."""
    import json

    repo = str(tmp_path)
    run_file = str(tmp_path / "r1.json")
    with open(run_file, "w") as handle:
        json.dump(
            {"schema": "driveros.commitmsg.v1", "proposed_message": "feat: x"}, handle
        )
    _record(repo, "r1", "main", ["a.py"], "feat: x", run_file, created_at=100.0)
    mark_seeded(repo, "r1", now_unix=110.0)
    with (
        patch("noidea.dogfood.get_commit_message", return_value="feat: x"),
        patch("noidea.dogfood.get_head_sha", return_value="sha1"),
    ):
        reconcile(repo, TTL, now_unix=120.0)
    with open(run_file) as handle:
        record = json.load(handle)
    assert record["verdict"]["disposition"] == ACCEPTED
    assert record["verdict"]["commit_sha"] == "sha1"


# ---- expiry → discarded ----


def test_expired_proposal_is_discarded(tmp_path):
    """A proposal never committed within the TTL is labelled discarded on the next prune."""
    import json

    repo = str(tmp_path)
    run_file = str(tmp_path / "r1.json")
    with open(run_file, "w") as handle:
        json.dump({"proposed_message": "feat: x"}, handle)
    _record(repo, "r1", "main", ["a.py"], "feat: x", run_file, created_at=100.0)
    # Queue a second proposal far in the future; record_proposal prunes the expired first one.
    _record(
        repo,
        "r2",
        "main",
        ["a.py"],
        "feat: y",
        "/x/r2.json",
        created_at=100.0 + TTL + 5,
    )
    with open(run_file) as handle:
        record = json.load(handle)
    assert record["verdict"]["disposition"] == DISCARDED


# ---- ids ----


def test_run_file_for_uses_dogfood_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("NOIDEA_DOGFOOD_DIR", str(tmp_path))
    run_id = new_run_id(now_unix=1700000000.0)
    path = run_file_for(run_id)
    assert path.startswith(str(tmp_path)) and path.endswith(f"{run_id}.json")

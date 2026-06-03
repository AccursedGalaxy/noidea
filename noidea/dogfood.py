"""The agent-backend dogfood loop: queue a proposal, seed it into a commit, reconcile the verdict.

driver-os generates a commit message ahead of the commit (`noidea suggest --agent`). We log
that *proposal* to a per-repo queue and archive its full agent trace. The prepare-commit-msg
hook later seeds the queued message into the commit buffer verbatim (no LLM — the agent already
ran), so the committed message genuinely descends from the agent draft. The post-commit hook
then reconciles: it compares the proposal against what the human actually committed and records
the verdict (accepted / modified / discarded) plus a raw similarity score, turning every commit
into a labelled dogfood example.

State is machine-local and per-repo under ``.git/noidea/``: an append-only ``pending.jsonl``
event log (propose / consume) and a single ``seeded.json`` pointer naming the proposal bound to
the next commit. The canonical record (the agent trace + the verdict) lives in the dogfood dir.
See the design grill for why: append-only sidesteps the proposal-vs-reconcile race, and the
seed pointer makes the hook the deterministic binding point.
"""

from __future__ import annotations

import difflib
import json
import os
import time
import uuid
from dataclasses import dataclass

from noidea.git import get_commit_message, get_head_sha

DOGFOOD_DIR_ENV = "NOIDEA_DOGFOOD_DIR"
_DEFAULT_DOGFOOD_DIR = os.path.expanduser("~/.noidea/dogfood")

# Per-repo state lives under .git/noidea/: machine-local, auto-ignored by git, and self-scoping
# so two repos committing at once never contend on a shared file. See the grill (machine-local
# is the deliberate scope — the queue does not follow clones/worktrees).
_REPO_STATE_DIRNAME = os.path.join(".git", "noidea")
_PENDING_FILENAME = "pending.jsonl"
_SEEDED_FILENAME = "seeded.json"

# The verdict a reconcile assigns. accepted = committed verbatim (similarity 1.0 after the same
# whitespace cleanup git applies); modified = committed but changed (the score carries how much,
# from a typo fix to a full rewrite — one bucket by design, no tuned floor); discarded = the
# proposal expired in the queue without ever being committed.
ACCEPTED = "accepted"
MODIFIED = "modified"
DISCARDED = "discarded"


@dataclass
class Proposal:
    """One queued agent proposal: the message and the context needed to match it to a commit."""

    run_id: str
    branch: str
    staged_files: list[str]
    proposed_message: str
    run_file: str
    created_at_unix: float


def dogfood_dir() -> str:
    """The directory holding canonical run records; overridable for CI artifact upload."""
    path = os.environ.get(DOGFOOD_DIR_ENV) or _DEFAULT_DOGFOOD_DIR
    assert isinstance(path, str) and path, "dogfood_dir must be a non-empty path"
    return path


def new_run_id(now_unix: float | None = None) -> str:
    """A sortable, unique id for one generation run: unix seconds plus a short random tail."""
    stamp = int(now_unix if now_unix is not None else time.time())
    run_id = f"{stamp}-{uuid.uuid4().hex[:8]}"
    assert isinstance(run_id, str) and "-" in run_id, "run_id must be 'stamp-rand'"
    return run_id


def run_file_for(run_id: str) -> str:
    """The path of the canonical run record (agent trace + later verdict) for a run id."""
    assert isinstance(run_id, str) and run_id, "run_id must be a non-empty string"
    path = os.path.join(dogfood_dir(), "runs", f"{run_id}.json")
    assert path.endswith(".json"), "run_file must be a .json path"
    return path


def normalize_message(message: str) -> str:
    """Apply git's own commit-message cleanup so an accepted-verbatim message compares equal.

    git strips per-line trailing whitespace and leading/trailing blank lines on commit, so the
    committed message is never byte-identical to the proposal even when nothing was edited. We
    mirror exactly that, plus EOL normalization, before any similarity is computed.
    """
    assert isinstance(message, str), "message must be a string"
    lines = message.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines = [line.rstrip() for line in lines]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    result = "\n".join(lines)
    assert isinstance(result, str), "result must be a string"
    return result


def message_similarity(left: str, right: str) -> float:
    """Normalized similarity in [0,1] between two messages; 1.0 means identical after cleanup.

    difflib (stdlib) keeps this dependency-free; the raw ratio is the signal, and the
    accepted/modified split downstream uses == 1.0, never a tuned threshold (see the grill).
    """
    assert isinstance(left, str) and isinstance(right, str), "inputs must be strings"
    normalized_left, normalized_right = (
        normalize_message(left),
        normalize_message(right),
    )
    if normalized_left == normalized_right:
        return 1.0
    ratio = difflib.SequenceMatcher(None, normalized_left, normalized_right).ratio()
    assert 0.0 <= ratio <= 1.0, "ratio must be in [0,1]"
    return ratio


def classify(proposal_message: str, committed_message: str) -> tuple[str, float]:
    """Label a committed message against its proposal: (disposition, similarity). Pure.

    Only accepted/modified are decided here — discarded is a queue-expiry state, not a commit
    outcome. The hook stays dumb: it records the score, downstream analysis picks any cutoffs.
    """
    assert isinstance(proposal_message, str), "proposal_message must be a string"
    assert isinstance(committed_message, str), "committed_message must be a string"
    similarity = message_similarity(proposal_message, committed_message)
    disposition = ACCEPTED if similarity == 1.0 else MODIFIED
    assert disposition in (ACCEPTED, MODIFIED), (
        "disposition must be accepted or modified"
    )
    return disposition, similarity


# ---- per-repo state paths ----


def _repo_state_dir(repo_root: str) -> str:
    assert isinstance(repo_root, str) and repo_root, (
        "repo_root must be a non-empty string"
    )
    return os.path.join(repo_root, _REPO_STATE_DIRNAME)


def _pending_path(repo_root: str) -> str:
    return os.path.join(_repo_state_dir(repo_root), _PENDING_FILENAME)


def _seeded_path(repo_root: str) -> str:
    return os.path.join(_repo_state_dir(repo_root), _SEEDED_FILENAME)


def _ensure_dir(path: str) -> bool:
    """Create a directory if absent; return False (never raise) so callers degrade gracefully."""
    assert isinstance(path, str) and path, "path must be a non-empty string"
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except OSError:
        return False


# ---- append-only pending event log ----


def _read_events(repo_root: str) -> list[dict]:
    """Read the pending event log; a missing file is an empty log and bad lines are skipped."""
    path = _pending_path(repo_root)
    if not os.path.exists(path):
        return []
    events: list[dict] = []
    try:
        with open(path) as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    continue  # A torn/corrupt line must not poison the whole log.
                if isinstance(parsed, dict):
                    events.append(parsed)
    except OSError:
        return []
    assert isinstance(events, list), "events must be a list"
    return events


def _append_event(repo_root: str, event: dict) -> bool:
    """Append one event as a JSON line (O_APPEND). Best-effort: returns False, never raises."""
    assert isinstance(event, dict) and event.get("event"), "event must be a tagged dict"
    if not _ensure_dir(_repo_state_dir(repo_root)):
        return False
    try:
        with open(_pending_path(repo_root), "a") as handle:
            handle.write(json.dumps(event) + "\n")
        return True
    except OSError:
        return False


def _open_proposals(events: list[dict]) -> list[Proposal]:
    """Fold the event log into the proposals that are still open (proposed, not yet consumed)."""
    assert isinstance(events, list), "events must be a list"
    consumed = {
        e["run_id"] for e in events if e.get("event") == "consume" and e.get("run_id")
    }
    proposals: list[Proposal] = []
    for event in events:
        if event.get("event") != "propose" or event.get("run_id") in consumed:
            continue
        proposals.append(
            Proposal(
                run_id=event.get("run_id", ""),
                branch=event.get("branch", ""),
                staged_files=list(event.get("staged_files", [])),
                proposed_message=event.get("proposed_message", ""),
                run_file=event.get("run_file", ""),
                created_at_unix=float(event.get("created_at_unix", 0.0)),
            )
        )
    proposals.sort(key=lambda p: p.created_at_unix)
    return proposals


def record_proposal(
    repo_root: str,
    run_id: str,
    branch: str,
    staged_files: list[str],
    message: str,
    run_file: str,
    ttl_seconds: int,
    now_unix: float | None = None,
) -> bool:
    """Queue a generated proposal for the hook to seed, and prune any expired proposals first."""
    assert isinstance(run_id, str) and run_id, "run_id must be a non-empty string"
    assert isinstance(message, str) and message.strip(), "message must be non-empty"
    now = now_unix if now_unix is not None else time.time()
    _prune_expired(repo_root, ttl_seconds, now)
    return _append_event(
        repo_root,
        {
            "event": "propose",
            "run_id": run_id,
            "branch": branch,
            "staged_files": list(staged_files),
            "proposed_message": message,
            "run_file": run_file,
            "created_at_unix": now,
        },
    )


def find_fresh_proposal(
    repo_root: str,
    staged_files_now: list[str],
    branch: str,
    ttl_seconds: int,
    now_unix: float | None = None,
) -> Proposal | None:
    """The newest open proposal for this branch, within the TTL, whose paths overlap the index.

    The path-overlap gate is what stops a stale proposal for one change from seeding an unrelated
    commit's buffer (the grilled UX failure mode); the TTL is only a backstop behind it.
    """
    assert isinstance(staged_files_now, list), "staged_files_now must be a list"
    now = now_unix if now_unix is not None else time.time()
    staged_now = set(staged_files_now)
    matches = [
        proposal
        for proposal in _open_proposals(_read_events(repo_root))
        if proposal.branch == branch
        and now - proposal.created_at_unix < ttl_seconds
        and staged_now & set(proposal.staged_files)
    ]
    return matches[-1] if matches else None  # _open_proposals is sorted oldest→newest.


def _prune_expired(repo_root: str, ttl_seconds: int, now_unix: float) -> None:
    """Label every open proposal past the TTL as discarded — the human never committed it.

    Idempotent (only acts on still-open proposals) and best-effort. Called on each propose and
    reconcile so the log self-cleans and the dogfood corpus gains its negative examples.
    """
    assert isinstance(ttl_seconds, int) and ttl_seconds > 0, (
        "ttl_seconds must be positive"
    )
    for proposal in _open_proposals(_read_events(repo_root)):
        if now_unix - proposal.created_at_unix < ttl_seconds:
            continue
        _consume(repo_root, proposal, DISCARDED, 0.0, "", "", now_unix)


# ---- seeded pointer (the proposal bound to the next commit) ----


def mark_seeded(repo_root: str, run_id: str, now_unix: float | None = None) -> bool:
    """Record which proposal the hook just seeded, so post-commit reconciles that exact one."""
    assert isinstance(run_id, str) and run_id, "run_id must be a non-empty string"
    now = now_unix if now_unix is not None else time.time()
    if not _ensure_dir(_repo_state_dir(repo_root)):
        return False
    try:
        with open(_seeded_path(repo_root), "w") as handle:
            json.dump({"run_id": run_id, "seeded_at_unix": now}, handle)
        return True
    except OSError:
        return False


def read_seeded(repo_root: str) -> dict | None:
    """The proposal bound to the next commit, or None when the last commit used the fast path."""
    path = _seeded_path(repo_root)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) and data.get("run_id") else None


def clear_seeded(repo_root: str) -> None:
    """Drop the seed pointer (best-effort): a fast-path commit must not reconcile a stale one."""
    try:
        os.remove(_seeded_path(repo_root))
    except OSError:
        pass  # Already absent, or unwritable — either way there is nothing to reconcile.


# ---- reconcile (post-commit) ----


@dataclass
class ReconcileResult:
    """The outcome of reconciling one commit against its seeded proposal."""

    run_id: str
    disposition: str
    similarity: float


def reconcile(
    repo_root: str, ttl_seconds: int, now_unix: float | None = None
) -> ReconcileResult | None:
    """Compare the just-made commit to its seeded proposal and record the human verdict.

    Returns None when there is nothing to reconcile (a fast-path or non-noidea commit). Pure
    plumbing — no LLM — and best-effort: it must never fail a commit, so it swallows IO errors.
    The amend case (the seeded proposal already consumed) recomputes against the new message and
    updates the record in place; rebase/squash are deliberately out of scope for v1.
    """
    now = now_unix if now_unix is not None else time.time()
    _prune_expired(repo_root, ttl_seconds, now)
    seeded = read_seeded(repo_root)
    if seeded is None:
        return None
    proposal = _proposal_by_run_id(repo_root, seeded["run_id"])
    clear_seeded(
        repo_root
    )  # One commit consumes the pointer regardless of the outcome below.
    if proposal is None:
        return None
    committed_message = get_commit_message("HEAD")
    disposition, similarity = classify(proposal.proposed_message, committed_message)
    _consume(
        repo_root,
        proposal,
        disposition,
        similarity,
        committed_message,
        get_head_sha(),
        now,
    )
    result = ReconcileResult(proposal.run_id, disposition, similarity)
    assert result.disposition in (ACCEPTED, MODIFIED), (
        "reconcile must label accepted or modified"
    )
    return result


def _proposal_by_run_id(repo_root: str, run_id: str) -> Proposal | None:
    """Find an open proposal by id; None if it is absent or already consumed (e.g. an amend)."""
    assert isinstance(run_id, str) and run_id, "run_id must be a non-empty string"
    for proposal in _open_proposals(_read_events(repo_root)):
        if proposal.run_id == run_id:
            return proposal
    return None


def _consume(
    repo_root: str,
    proposal: Proposal,
    disposition: str,
    similarity: float,
    final_message: str,
    commit_sha: str,
    now_unix: float,
) -> None:
    """Tombstone the proposal in the log and write its verdict into the canonical run record.

    Two writes, both best-effort: the consume event closes the proposal in the queue, and the
    run-record update makes it a labelled dogfood example. Neither may fail the commit.
    """
    assert disposition in (ACCEPTED, MODIFIED, DISCARDED), (
        "disposition must be a known label"
    )
    assert 0.0 <= similarity <= 1.0, "similarity must be in [0,1]"
    _append_event(
        repo_root,
        {
            "event": "consume",
            "run_id": proposal.run_id,
            "disposition": disposition,
            "similarity": similarity,
            "final_message": final_message,
            "commit_sha": commit_sha,
            "consumed_at_unix": now_unix,
        },
    )
    _update_run_verdict(
        proposal.run_file,
        {
            "disposition": disposition,
            "similarity": similarity,
            "final_message": final_message,
            "commit_sha": commit_sha,
            "reconciled_at_unix": now_unix,
        },
    )


def _update_run_verdict(run_file: str, verdict: dict) -> None:
    """Append the human verdict to the driver-os trace record. Best-effort: never raises.

    A missing or corrupt record (the agent run may have failed before writing one) just means
    no labelled example for this proposal — not a reason to break the post-commit hook.
    """
    assert isinstance(verdict, dict) and verdict, "verdict must be a non-empty dict"
    if not run_file or not os.path.exists(run_file):
        return
    try:
        with open(run_file) as handle:
            record = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(record, dict):
        return
    record["verdict"] = verdict
    try:
        with open(run_file, "w") as handle:
            json.dump(record, handle, indent=2)
    except OSError:
        pass

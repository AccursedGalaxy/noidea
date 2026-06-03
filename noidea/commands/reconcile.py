"""Hidden post-commit command: reconcile the just-made commit against its seeded agent proposal.

Wired to the post-commit git hook (see git.HOOKS). It records the human verdict — accepted,
modified, or discarded, plus a raw similarity score — turning every commit into a labelled
dogfood example. Best-effort and silent: git ignores post-commit's exit status, and a capture
failure must never disrupt the developer's commit flow, so this swallows everything.
"""

from noidea import dogfood
from noidea.config import load_config
from noidea.git import get_git_root


def reconcile() -> None:
    """Record the accept/edit/discard verdict for the commit just made; never raises."""
    repo_root = get_git_root()
    if not repo_root:
        return
    cfg = load_config()
    # dogfood.reconcile is itself best-effort; the broad guard is the last line of defense so a
    # surprise (e.g. an unreadable run record) can never turn into a non-zero post-commit exit.
    try:
        dogfood.reconcile(repo_root, cfg.agent_proposal_ttl_seconds)
    except Exception:  # noqa: BLE001 — a dogfood capture must never break a commit.
        pass

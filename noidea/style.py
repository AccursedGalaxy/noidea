"""Repo-native commit style learning: distil recent commits into a StyleProfile.

The analysis is pure (no git, no API), so it is unit-testable with canned commits.
suggest() renders the profile into the prompt so generated messages match the repo's
voice instead of generic conventional-commit boilerplate.
"""

import re
from collections import Counter
from dataclasses import dataclass

from noidea.git import Commit

# How many recent commits to sample. Enough for stable ratios, recent enough to reflect
# current conventions; a single fast git call with no API cost.
SAMPLE_SIZE = 50

# Below this many commits the ratios are dominated by single commits and mislead more
# than they help, so we produce no profile and the caller keeps default behavior.
MIN_COMMITS = 5

# Keep only the most-used scopes so the prompt hint leads with the repo's dominant
# vocabulary and stays compact on repos that have accumulated many one-off scopes.
SCOPE_LIMIT_MAX = 8

# A conventional-commit subject: type, optional (scope), optional !, then ": ".
_CONVENTIONAL_RE = re.compile(r"^(\w+)(?:\(([^)]+)\))?!?: ")

# A gitmoji prefix: either a :shortcode: or a leading emoji from the common emoji blocks
# (misc symbols/dingbats U+2600-27BF, misc symbols-and-arrows U+2B00-2BFF, and the
# supplementary emoji plane U+1F000-1FAFF that covers most gitmoji).
_GITMOJI_RE = re.compile(r"^\s*(?::[a-z0-9_+-]+:|[☀-➿⬀-⯿\U0001f000-\U0001faff])")

# A repo "uses gitmoji" only when the habit is dominant, not when one commit slipped one in.
_GITMOJI_RATIO_MIN = 0.5

# Above this share of conventional subjects we treat the repo as conventional and enforce
# the format; below it we drop the type(scope): prefix to match the repo's plain style.
CONVENTIONAL_THRESHOLD = 0.7

# Body-habit bands: at/above HIGH the repo habitually writes bodies; at/below LOW it rarely
# does; between, we state the observed share rather than push either way.
_BODY_RATIO_HIGH = 0.5
_BODY_RATIO_LOW = 0.15


def _median_int(values: list[int]) -> int:
    """Median of a non-empty list of ints, rounded to an int for even-length samples."""
    assert values, "values must be non-empty"
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        result = ordered[middle]
    else:
        result = round((ordered[middle - 1] + ordered[middle]) / 2)
    assert result >= 0, "median of non-negative lengths must be non-negative"
    return result


@dataclass(frozen=True)
class StyleProfile:
    """The repo's observed commit conventions, distilled from a sample of its log."""

    scopes: tuple[str, ...]
    conventional_ratio: float
    body_ratio: float
    subject_length_chars_median: int
    uses_gitmoji: bool

    def __post_init__(self):
        assert isinstance(self.scopes, tuple), "scopes must be a tuple"
        assert 0.0 <= self.conventional_ratio <= 1.0, "conventional_ratio must be in 0..1"
        assert 0.0 <= self.body_ratio <= 1.0, "body_ratio must be in 0..1"
        assert self.subject_length_chars_median >= 0, "median length must be non-negative"
        assert isinstance(self.uses_gitmoji, bool), "uses_gitmoji must be a bool"


def analyze_commits(commits: list[Commit]) -> StyleProfile | None:
    """Distil a sample of commits into a StyleProfile, or None if there is too little signal."""
    assert isinstance(commits, list), "commits must be a list"

    if len(commits) < MIN_COMMITS:
        return None

    conventional_count = 0
    body_count = 0
    gitmoji_count = 0
    scope_counts: Counter[str] = Counter()
    subject_lengths: list[int] = []
    for commit in commits:
        subject_lengths.append(len(commit.subject))
        if commit.body.strip():
            body_count += 1
        if _GITMOJI_RE.match(commit.subject):
            gitmoji_count += 1
        match = _CONVENTIONAL_RE.match(commit.subject)
        if match:
            conventional_count += 1
            scope = match.group(2)
            if scope:
                scope_counts[scope] += 1

    # most_common orders by count desc and breaks ties by first-seen, so the hint leads
    # with the dominant scopes; cap keeps it compact on repos with many one-off scopes.
    top_scopes = tuple(scope for scope, _ in scope_counts.most_common(SCOPE_LIMIT_MAX))
    sample_size = len(commits)
    profile = StyleProfile(
        scopes=top_scopes,
        conventional_ratio=conventional_count / sample_size,
        body_ratio=body_count / sample_size,
        subject_length_chars_median=_median_int(subject_lengths),
        uses_gitmoji=gitmoji_count / sample_size >= _GITMOJI_RATIO_MIN,
    )
    assert isinstance(profile, StyleProfile), "analyze_commits must return a StyleProfile"
    return profile


def render_profile(profile: StyleProfile) -> str:
    """Render the profile as a 'Repo commit conventions:' block for the prompt.

    Applies the precedence rules: the quality floor stays in the system prompt; this block
    only refines within it (additive scopes/gitmoji, tighten-only subject length) except for
    the one honored contradiction — dropping the conventional prefix when the repo lacks it.
    """
    assert isinstance(profile, StyleProfile), "profile must be a StyleProfile"

    lines: list[str] = ["Repo commit conventions:"]
    if profile.conventional_ratio >= CONVENTIONAL_THRESHOLD:
        if profile.scopes:
            scope_list = ", ".join(profile.scopes)
            lines.append(f"- this repo uses conventional commits; reuse its scopes: {scope_list}")
        else:
            lines.append("- this repo uses conventional commits; keep the type: prefix")
    else:
        lines.append(
            "- this repo does not use conventional-commit prefixes; do not add a "
            "type(scope): prefix, match its plain subject style"
        )

    # Tighten the subject target toward the repo's median, but never loosen past the 72-char
    # quality floor the system prompt already enforces.
    subject_target = min(72, profile.subject_length_chars_median)
    lines.append(f"- aim for subjects around {subject_target} characters")

    # Follow the repo's body habit. An extra body is never a quality regression, so this is
    # allowed to loosen the default "only if non-obvious" rule when the repo writes bodies.
    if profile.body_ratio >= _BODY_RATIO_HIGH:
        lines.append("- most commits here include a short body; include one")
    elif profile.body_ratio <= _BODY_RATIO_LOW:
        lines.append("- commits here rarely include a body; usually omit it")
    else:
        body_percent = round(profile.body_ratio * 100)
        lines.append(f"- about {body_percent}% of commits include a body; add one when it helps")

    if profile.uses_gitmoji:
        lines.append("- this repo prefixes subjects with a gitmoji; do the same")

    rendered = "\n".join(lines)
    assert rendered.startswith("Repo commit conventions:"), "render must produce the block header"
    return rendered

"""Tests for repo-native commit style learning: analysis and rendering."""

from dataclasses import replace

from noidea.git import Commit
from noidea.style import StyleProfile, analyze_commits, render_profile


def test_conventional_repo_is_recognized_with_its_scopes():
    """A repo whose history uses conventional commits is profiled as conventional,
    and the scopes it actually uses are surfaced for reuse."""
    commits = [
        Commit("feat(cli): add suggest command", ""),
        Commit("fix(provider): handle rate limits", ""),
        Commit("refactor(config): collapse merge", ""),
        Commit("feat(cli): add status output", ""),
        Commit("docs(provider): document errors", ""),
    ]

    profile = analyze_commits(commits)

    assert profile is not None
    assert profile.conventional_ratio == 1.0
    assert set(profile.scopes) == {"cli", "provider", "config"}


def test_scopes_are_ranked_by_frequency_and_capped():
    """Scopes are ordered most-used first and capped, so the prompt hint stays compact
    and leads with the repo's dominant scopes rather than whatever appeared first."""
    # cli x4, provider x2, then nine distinct one-off scopes.
    commits = (
        [Commit(f"feat(cli): change {i}", "") for i in range(4)]
        + [Commit(f"fix(provider): change {i}", "") for i in range(2)]
        + [Commit(f"chore(scope{i}): change", "") for i in range(9)]
    )

    profile = analyze_commits(commits)

    assert profile is not None
    # Most frequent first; ties (the one-offs) keep first-seen order.
    assert profile.scopes[:2] == ("cli", "provider")
    # Capped to the top 8 even though 11 distinct scopes were seen.
    assert len(profile.scopes) == 8


def test_too_few_commits_yields_no_profile():
    """Below the minimum sample, ratios are meaningless, so no profile is produced
    and callers fall back to default behavior."""
    commits = [Commit(f"feat: change {i}", "") for i in range(4)]

    assert analyze_commits(commits) is None


def test_body_ratio_reflects_how_often_commits_have_bodies():
    """A repo where most commits carry an explanatory body is profiled as body-writing."""
    commits = [
        Commit("feat: a", "why a happened"),
        Commit("feat: b", "why b happened"),
        Commit("feat: c", "why c happened"),
        Commit("fix: d", ""),
        Commit("fix: e", ""),
    ]

    profile = analyze_commits(commits)

    assert profile is not None
    assert profile.body_ratio == 0.6


def test_subject_length_is_the_median_of_observed_subjects():
    """The profile captures the repo's typical subject length via the median, so a
    single very long or short subject does not skew it."""
    # Subject lengths: 10, 20, 30, 40, 200 -> median is 30.
    commits = [
        Commit("a" * 10, ""),
        Commit("b" * 20, ""),
        Commit("c" * 30, ""),
        Commit("d" * 40, ""),
        Commit("e" * 200, ""),
    ]

    profile = analyze_commits(commits)

    assert profile is not None
    assert profile.subject_length_chars_median == 30


def test_gitmoji_repo_is_recognized():
    """A repo that prefixes subjects with gitmoji (emoji or :shortcode:) is profiled
    as using gitmoji; a plain repo is not."""
    gitmoji_commits = [
        Commit("✨ feat: add suggest", ""),
        Commit("🐛 fix: handle empty diff", ""),
        Commit(":rocket: chore: release", ""),
        Commit("✨ feat: add status", ""),
        Commit("refactor: tidy imports", ""),
    ]
    plain_commits = [Commit(f"feat: change {i}", "") for i in range(5)]

    gitmoji_profile = analyze_commits(gitmoji_commits)
    plain_profile = analyze_commits(plain_commits)

    assert gitmoji_profile is not None and gitmoji_profile.uses_gitmoji is True
    assert plain_profile is not None and plain_profile.uses_gitmoji is False


def test_gitmoji_prefix_does_not_hide_conventional_structure():
    """A repo that uses gitmoji AND conventional commits is recognized as both: the
    leading gitmoji must not stop the conventional type/scope from being detected."""
    commits = [
        Commit("✨ feat(cli): add suggest command", ""),
        Commit("🐛 fix(provider): handle rate limits", ""),
        Commit(":rocket: chore(release): cut 1.0.3", ""),
        Commit("✨ feat(cli): add status output", ""),
        Commit("♻️ refactor(config): collapse merge", ""),
    ]

    profile = analyze_commits(commits)

    assert profile is not None
    # The gitmoji prefix is stripped before the conventional check, so every subject counts.
    assert profile.conventional_ratio == 1.0
    assert profile.uses_gitmoji is True
    assert set(profile.scopes) == {"cli", "provider", "release", "config"}


def _profile(**overrides) -> StyleProfile:
    """A StyleProfile with sane defaults, overridable per render test."""
    base = StyleProfile(
        scopes=(),
        conventional_ratio=1.0,
        body_ratio=0.0,
        subject_length_chars_median=50,
        uses_gitmoji=False,
    )
    return replace(base, **overrides)


def test_render_conventional_repo_instructs_conventional_format_with_scopes():
    """When the repo uses conventional commits, the rendered guidance keeps the format
    and surfaces the repo's own scope vocabulary for reuse."""
    profile = _profile(conventional_ratio=1.0, scopes=("cli", "provider"))

    rendered = render_profile(profile)

    assert "conventional" in rendered.lower()
    assert "cli" in rendered and "provider" in rendered


def test_render_non_conventional_repo_drops_the_prefix():
    """When the repo plainly does not use conventional commits, the guidance tells the
    model to match that — no type(scope): prefix — rather than impose the format."""
    profile = _profile(conventional_ratio=0.1, scopes=())

    rendered = render_profile(profile).lower()

    assert "not" in rendered and "prefix" in rendered


def test_render_subject_length_tightens_but_never_loosens():
    """A repo with short subjects pulls the target down; a repo with long subjects is
    still capped at the 72-char quality floor."""
    short = render_profile(_profile(subject_length_chars_median=45))
    long = render_profile(_profile(subject_length_chars_median=90))

    assert "45" in short
    assert "90" not in long and "72" in long


def test_render_body_habit_follows_the_repo():
    """A repo that usually writes bodies is told to include one; a repo that rarely does
    is told to usually omit it."""
    body_heavy = render_profile(_profile(body_ratio=0.8)).lower()
    body_light = render_profile(_profile(body_ratio=0.05)).lower()

    assert "body" in body_heavy and "include" in body_heavy
    assert "body" in body_light and ("omit" in body_light or "rarely" in body_light)


def test_render_mentions_gitmoji_only_when_the_repo_uses_it():
    """A gitmoji repo is told to prefix with a gitmoji; a plain repo gets no such line."""
    with_gitmoji = render_profile(_profile(uses_gitmoji=True)).lower()
    without_gitmoji = render_profile(_profile(uses_gitmoji=False)).lower()

    assert "gitmoji" in with_gitmoji or "emoji" in with_gitmoji
    assert "gitmoji" not in without_gitmoji and "emoji" not in without_gitmoji

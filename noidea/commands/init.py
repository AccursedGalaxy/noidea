from noidea.git import HookOutcome, install_hook

# One line per outcome, so re-running init in an already wired repo says what actually happened.
INIT_WORDING = {
    HookOutcome.INSTALLED: "Hook installed. You're all set — commit away, we'll handle the words.",
    HookOutcome.UPDATED: "Hook updated to the latest version. Carry on committing.",
    HookOutcome.UNCHANGED: "Hook already up to date. Nothing to do.",
}


def init():
    """Set up the magic. Installs the git hook so commits write themselves."""
    result = install_hook()
    if result.success:
        print(INIT_WORDING[result.outcome])
    else:
        print(f"Couldn't install the hook: {result.error}")

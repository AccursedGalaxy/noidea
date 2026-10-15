# Reproducible README demo. Render with: vhs assets/demo.tape  (writes assets/demo.gif)
#
# Runs in a clean bash with a throwaway repo, so no personal shell plugins, prompts, or old hooks
# end up in the recording. Needs `noidea` on PATH and a provider key (keyring or env var).

Output assets/demo.gif

Set Shell "bash"
Set FontSize 18
Set Width 1300
Set Height 600
Set Padding 24
Set TypingSpeed 45ms
Set Theme "GitHub Dark"

Hide
Type "export PS1='\[\e[32m\]demo\[\e[0m\] $ ' GIT_EDITOR='nvim --clean' EDITOR='nvim --clean'" Enter
Type "cd $(mktemp -d) && git init -q -b main && git config user.name demo && git config user.email demo@example.com" Enter
Type "printf 'def add(a, b):\n    return a + b\n' > calc.py && git add calc.py && git commit -qm 'feat: add calc module'" Enter
Type `printf '\n\ndef divide(a, b):\n    if b == 0:\n        raise ValueError("division by zero")\n    return a / b\n' >> calc.py` Enter
Type "clear" Enter
Show

Type "noidea init" Sleep 400ms Enter
Sleep 1.5s
Type "git add calc.py" Sleep 300ms Enter
Sleep 500ms
Type "git commit" Sleep 400ms Enter
# Wait for the model, then show the pre-filled message in the editor before saving it.
Sleep 6s
Sleep 2.5s
Type ":wq" Sleep 300ms Enter
Sleep 1.5s
Type "git log --oneline -2" Sleep 300ms Enter
Sleep 3s

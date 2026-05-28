Source demos/_settings.tape

Output demos/quickstart.gif
Output demos/quickstart.mp4

Hide
Type `eval "$(pixi shell-hook -s bash -e dev)"`
Enter
Wait /\)/
Type `export PS1="$DEMO_PS1" && export SHELL=/bin/bash && export FIXTURES="$(pwd)/demos/fixtures" && export CONDA_EXEC_HOME=/tmp/conda-exec-demo-quickstart && rm -rf "$CONDA_EXEC_HOME" /tmp/conda-exec-demo-quickstart-work && mkdir -p /tmp/conda-exec-demo-quickstart-work && cd /tmp/conda-exec-demo-quickstart-work`
Enter
Wait /\$/
Type `cp "$FIXTURES/lint_target.py" .`
Enter
Wait /\$/
Type "clear"
Enter
Wait /\$/
Sleep 500ms
Show

Type "# Run a conda package without installing it permanently"
Enter
Sleep 500ms

Type@80ms "bat lint_target.py"
Enter
Wait /\$/
Sleep 2s

Type "# First run creates and caches a ruff environment"
Enter
Sleep 500ms

Type@80ms "conda exec ruff check ."
Enter
Wait /\$/
Sleep 2s

Type "# Run again: same command, cached environment"
Enter
Sleep 500ms

Type@80ms "conda exec ruff check ."
Enter
Wait /\$/
Sleep 1s

Type "# The standalone ce command uses the same cache"
Enter
Sleep 500ms

Type@80ms "ce ruff check ."
Enter
Wait /\$/
Sleep 1s

Type "# See the disposable environment"
Enter
Sleep 500ms

Type@80ms "conda exec --list"
Enter
Wait /\$/
Sleep 3s

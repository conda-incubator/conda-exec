Source demos/_settings.tape

Output demos/pypi-script.gif
Output demos/pypi-script.mp4

Hide
Type `eval "$(pixi shell-hook -s bash -e test)"`
Enter
Wait /\)/
Type `export PS1="$DEMO_PS1" && export SHELL=/bin/bash && export FIXTURES="$(pwd)/demos/fixtures" && export CONDA_EXEC_HOME=/tmp/conda-exec-demo-pypi-script && rm -rf "$CONDA_EXEC_HOME" /tmp/conda-exec-demo-pypi-script-work && mkdir -p /tmp/conda-exec-demo-pypi-script-work && cd /tmp/conda-exec-demo-pypi-script-work`
Enter
Wait /\$/
Type `cp "$FIXTURES/rich_report.py" .`
Enter
Wait /\$/
Type "clear"
Enter
Wait /\$/
Sleep 500ms
Show

Type "# Mix PyPI and conda dependencies in one script"
Enter
Sleep 500ms

Type@80ms "bat --line-range 1:8 rich_report.py"
Enter
Wait /\$/
Sleep 3s

Type "# conda-exec combines both dependency sources"
Enter
Sleep 500ms

Type@80ms "conda exec rich_report.py"
Enter
Wait /\$/
Sleep 3s

Type "# The cache makes the second run fast"
Enter
Sleep 500ms

Type@80ms "conda exec rich_report.py"
Enter
Wait /\$/
Sleep 2s

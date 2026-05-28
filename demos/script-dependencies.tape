Source demos/_settings.tape

Output demos/script-dependencies.gif
Output demos/script-dependencies.mp4

Hide
Type `eval "$(pixi shell-hook -s bash -e dev)"`
Enter
Wait /\)/
Type `export PS1="$DEMO_PS1" && export SHELL=/bin/bash && export FIXTURES="$(pwd)/demos/fixtures" && export CONDA_EXEC_HOME=/tmp/conda-exec-demo-script-dependencies && rm -rf "$CONDA_EXEC_HOME" /tmp/conda-exec-demo-script-dependencies-work && mkdir -p /tmp/conda-exec-demo-script-dependencies-work && cd /tmp/conda-exec-demo-script-dependencies-work`
Enter
Wait /\$/
Type `cp "$FIXTURES/date_report.py" .`
Enter
Wait /\$/
Type "clear"
Enter
Wait /\$/
Sleep 500ms
Show

Type "# Scripts can declare conda dependencies inline"
Enter
Sleep 500ms

Type@80ms "bat date_report.py"
Enter
Wait /\$/
Sleep 4s

Type "# conda-exec reads the metadata and builds the environment"
Enter
Sleep 500ms

Type@80ms `conda exec date_report.py "May 28, 2026 10:30"`
Enter
Wait /\$/
Sleep 2s

Type "# Subsequent runs reuse the same script environment"
Enter
Sleep 500ms

Type@80ms `conda exec date_report.py "2026-06-01"`
Enter
Wait /\$/
Sleep 2s

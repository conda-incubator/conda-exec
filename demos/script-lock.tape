Source demos/_settings.tape

Output demos/script-lock.gif
Output demos/script-lock.mp4

Hide
Type `eval "$(pixi shell-hook -s bash -e dev)"`
Enter
Wait /\)/
Type `export PS1="$DEMO_PS1" && export SHELL=/bin/bash && export FIXTURES="$(pwd)/demos/fixtures" && export CONDA_EXEC_HOME=/tmp/conda-exec-demo-script-lock && rm -rf "$CONDA_EXEC_HOME" /tmp/conda-exec-demo-script-lock-work && mkdir -p /tmp/conda-exec-demo-script-lock-work && cd /tmp/conda-exec-demo-script-lock-work`
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

Type "# Generate repeatable lock data next to the script"
Enter
Sleep 500ms

Type@80ms `conda exec --lock date_report.py "May 28, 2026"`
Enter
Wait /\$/
Sleep 3s

Type "# Sidecar lock data is written beside the script"
Enter
Sleep 500ms

Type@80ms "ls -1"
Enter
Wait /\$/
Sleep 2s

Type@80ms "sed -n '1,12p' date_report.py.conda-exec.lock"
Enter
Wait /\$/
Sleep 3s

Type "# Clean the cache but keep the lock"
Enter
Sleep 500ms

Type@80ms "conda exec --clean --all --yes"
Enter
Wait /\$/
Sleep 2s

Type "# Normal runs use the lock before solving from metadata"
Enter
Sleep 500ms

Type@80ms `conda exec date_report.py "2026-05-29"`
Enter
Wait /\$/
Sleep 3s

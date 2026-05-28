Source demos/_settings.tape

Output demos/cache-management.gif
Output demos/cache-management.mp4

Hide
Type `eval "$(pixi shell-hook -s bash -e dev)"`
Enter
Wait /\)/
Type `export PS1="$DEMO_PS1" && export SHELL=/bin/bash && export CONDA_EXEC_HOME=/tmp/conda-exec-demo-cache-management && rm -rf "$CONDA_EXEC_HOME" /tmp/conda-exec-demo-cache-management-work && mkdir -p /tmp/conda-exec-demo-cache-management-work && cd /tmp/conda-exec-demo-cache-management-work`
Enter
Wait /\$/
Type "conda exec ruff -- --version > /dev/null 2>&1"
Enter
Wait /\$/
Type "conda exec python -- --version > /dev/null 2>&1"
Enter
Wait /\$/
Type "clear"
Enter
Wait /\$/
Sleep 500ms
Show

Type "# List cached environments with size and age"
Enter
Sleep 500ms

Type@80ms "conda exec --list"
Enter
Wait /\$/
Sleep 3s

Type "# JSON output is for automation"
Enter
Sleep 500ms

Type@80ms "conda exec --list --json"
Enter
Wait /\$/
Sleep 4s

Type "# Preview cleanup before removing anything"
Enter
Sleep 500ms

Type@80ms "conda exec --clean --all --dry-run"
Enter
Wait /\$/
Sleep 3s

Type "# Remove everything in this demo cache"
Enter
Sleep 500ms

Type@80ms "conda exec --clean --all --yes"
Enter
Wait /\$/
Sleep 2s

Type@80ms "conda exec --list"
Enter
Wait /\$/
Sleep 2s

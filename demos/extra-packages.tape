Source demos/_settings.tape

Output demos/extra-packages.gif
Output demos/extra-packages.mp4

Hide
Type `eval "$(pixi shell-hook -s bash -e dev)"`
Enter
Wait /\)/
Type `export PS1="$DEMO_PS1" && export SHELL=/bin/bash && export CONDA_EXEC_HOME=/tmp/conda-exec-demo-extra-packages && rm -rf "$CONDA_EXEC_HOME" /tmp/conda-exec-demo-extra-packages-work && mkdir -p /tmp/conda-exec-demo-extra-packages-work && cd /tmp/conda-exec-demo-extra-packages-work`
Enter
Wait /\$/
Type "clear"
Enter
Wait /\$/
Sleep 500ms
Show

Type "# Add runtime packages to the ephemeral tool environment"
Enter
Sleep 500ms

Type@80ms `conda exec --with rich python -- -c "from rich import print; print('[bold green]rich is available[/bold green]')"`
Enter
Wait /\$/
Sleep 3s

Type "# The -- separator keeps tool arguments from becoming conda-exec flags"
Enter
Sleep 500ms

Type@80ms `conda exec --with rich python -- -c "import sys; print(sys.executable)"`
Enter
Wait /\$/
Sleep 2s

Type "# Extra specs are part of the cache key"
Enter
Sleep 500ms

Type@80ms "conda exec --list"
Enter
Wait /\$/
Sleep 3s

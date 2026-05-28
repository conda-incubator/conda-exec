# Prior art

The idea of running tools from conda packages without a persistent install
has come up several times in the conda ecosystem.

## conda-execute (2015)

[conda-execute](https://github.com/conda-tools/conda-execute) by Phil Elson
allowed running Python scripts with inline dependency declarations embedded
in YAML comments. It created temporary environments from those inline specs
and cached them by hash. The project has been unmaintained since 2019
and its conda-forge feedstock is archived.

conda-exec builds on this concept with two key differences: it supports
both packaged CLI tools (`conda exec ruff`) and scripts with inline
metadata (`conda exec script.py`), and it uses the now-standardized
[PEP 723](https://peps.python.org/pep-0723/) TOML format instead of
YAML, with a `[tool.conda]` extension for conda-native dependencies.

## conda issue #2379 (2016)

[conda/conda#2379](https://github.com/conda/conda/issues/2379) requested a
fast way to execute commands inside existing environments without the
overhead of `conda activate`. The discussion led to `conda run`, which
shipped in conda 4.6 (2018).

conda-exec is complementary to `conda run`: while `conda run` executes
commands in environments that already exist, conda-exec creates ephemeral
cached environments on the fly from package specs. They address different
use cases.

## conda-exec shell script on conda-forge (2019)

A [minimal shell script](https://github.com/conda-forge/conda-exec-feedstock)
by Patrick Sodré that activates an existing conda environment and uses
`exec` to replace the process with a given command. It was last updated
in 2020 and has effectively zero downloads. It requires a full environment
path as input and does not create environments.

conda-exec is fundamentally different: it resolves package specs, creates
cached environments via the solver, discovers binaries, and manages the
cache lifecycle.

## Comparable tools in other ecosystems

conda-exec fills the same role as these tools in their respective ecosystems:

| Tool | Ecosystem | Example |
| ---- | --------- | ------- |
| [npx](https://docs.npmjs.com/cli/commands/npx) | Node.js | `npx prettier --write .` |
| [uvx](https://docs.astral.sh/uv/guides/tools/) | Python (uv) | `uvx ruff check .` |
| [pipx run](https://pipx.pypa.io/) | Python (pip) | `pipx run black .` |
| conda exec / ce | conda | `conda exec ruff check .` or `ce ruff check .` |

## PEP 723 and the `[tool.conda]` extension

[PEP 723](https://peps.python.org/pep-0723/) standardizes inline script
metadata in Python scripts using TOML in comment blocks. The standard
`dependencies` field declares PyPI packages, and `requires-python`
constrains the Python version.

conda-exec extends this with a `[tool.conda]` table for conda-native
dependencies:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["requests"]
#
# [tool.conda]
# channels = ["conda-forge", "bioconda"]
# dependencies = ["samtools>=1.19"]
# ///
```

When both PyPI and conda dependencies are declared, both dependency sets are
included in one environment solve. PyPI packages are resolved through the
[conda-pypi](https://github.com/conda/conda-pypi) channel so conda's solver
can handle the combined input.

Scripts with only `[tool.conda].dependencies` work without conda-pypi.
Scripts with only `dependencies` (PyPI) require conda-pypi to be installed.

### Forward compatibility

[PEP 725](https://peps.python.org/pep-0725/) and
[PEP 804](https://peps.python.org/pep-0804/) explore standardized ways to
describe external dependencies. conda-exec uses `[tool.conda]` today
because it is explicit, namespaced, and valid PEP 723 metadata.

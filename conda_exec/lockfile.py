"""Script lockfile discovery, embedding, import, and export."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

from conda.base.constants import KNOWN_SUBDIRS
from conda.base.context import context, env_name
from conda.exceptions import CondaError
from conda.gateways.disk.delete import rm_rf
from conda.gateways.disk.update import rename
from conda.models.environment import Environment
from conda.plugins.types import EnvironmentFormat

from .exceptions import ScriptLockError
from .script import extract_script_block

if TYPE_CHECKING:
    from .script import ScriptMetadata

MAX_LOCK_SIZE = 10 * 1024 * 1024
DEFAULT_LOCK_FORMAT = "rattler-lock-v6"
DEFAULT_LOCK_FILENAMES = ("conda-exec.lock",)

LOCK_BLOCK_TYPE = "conda-exec-lock"
LOCK_MARKER = f"# /// {LOCK_BLOCK_TYPE}"
LOCK_END = "# ///"
LOCK_INPUT_DIGEST_PREFIX = "# conda-exec-lock-input-sha256: "


@dataclass(frozen=True)
class ScriptLock:
    """Resolved script lock data."""

    source: str
    content: str
    path: Path | None = None


@dataclass(frozen=True)
class ScriptLockFormat:
    """Environment lockfile format registered with conda."""

    name: str
    default_filenames: tuple[str, ...]


class ScriptLockManager:
    """Manage script lock discovery, writing, export, and environment creation."""

    def __init__(self, format_name: str = DEFAULT_LOCK_FORMAT) -> None:
        self.format_name = format_name

    @cached_property
    def lock_format(self) -> ScriptLockFormat:
        """Resolve this lockfile format from conda exporter/specifier plugins."""
        plugin_manager = context.plugin_manager
        try:
            exporter = plugin_manager.get_environment_exporter_by_format(
                self.format_name
            )
            specifier = plugin_manager.get_environment_specifiers()[exporter.name]
        except KeyError as exc:
            raise ScriptLockError(
                f"lock specifier {self.format_name!r} is not available",
                hints=[
                    "install conda-lockfiles or choose a registered lockfile format"
                ],
            ) from exc
        except CondaError as exc:
            raise ScriptLockError(
                f"lock format {self.format_name!r} is not available: {exc}",
                hints=[
                    "install conda-lockfiles or choose a registered lockfile format"
                ],
            ) from exc

        if exporter.environment_format != EnvironmentFormat.lockfile:
            raise ScriptLockError(f"export format {exporter.name!r} is not a lockfile")
        if specifier.environment_format != EnvironmentFormat.lockfile:
            raise ScriptLockError(f"specifier {specifier.name!r} is not a lockfile")

        default_filenames = dict.fromkeys(
            [*exporter.default_filenames, *specifier.default_filenames]
        )
        if not default_filenames:
            raise ScriptLockError(
                f"lock format {exporter.name!r} does not define default filenames"
            )

        return ScriptLockFormat(
            name=exporter.name,
            default_filenames=tuple(default_filenames),
        )

    @cached_property
    def exporter(self):
        """Return the conda exporter plugin for the resolved lock format."""
        return context.plugin_manager.get_environment_exporter_by_format(
            self.lock_format.name
        )

    def sidecar_paths(self, script_path: Path) -> list[Path]:
        """Return supported sidecar lockfile paths for a script."""
        paths = []
        for filename in self.default_filenames():
            paths.extend(
                [
                    script_path.with_name(f"{script_path.name}.{filename}"),
                    script_path.with_name(f"{script_path.stem}.{filename}"),
                ]
            )
        return paths

    def default_filenames(self) -> tuple[str, ...]:
        """Return expected lockfile names without plugin lookup for the default."""
        if self.format_name == DEFAULT_LOCK_FORMAT:
            return DEFAULT_LOCK_FILENAMES
        return self.lock_format.default_filenames

    def default_sidecar_path(self, script_path: Path) -> Path:
        """Return the default sidecar lockfile path for a script."""
        return self.sidecar_paths(script_path)[0]

    def discover(
        self,
        script_path: Path,
        *,
        embedded_content: str | None = None,
        expected_input_digest: str | None = None,
        scan_embedded: bool = True,
    ) -> ScriptLock | None:
        """Discover embedded or sidecar script lock data in precedence order."""
        if (
            scan_embedded
            and embedded_content is None
            and script_path.stat().st_size <= MAX_LOCK_SIZE
        ):
            with script_path.open(encoding="utf-8") as source_file:
                embedded_content = extract_script_block(
                    source_file,
                    block_type=LOCK_BLOCK_TYPE,
                    strict=False,
                )

        if embedded_content and self.lock_matches_input(
            embedded_content,
            expected_input_digest,
        ):
            return ScriptLock(
                source="embedded",
                content=embedded_content,
                path=script_path,
            )

        for path in self.sidecar_paths(script_path):
            if not path.is_file():
                continue
            if path.stat().st_size > MAX_LOCK_SIZE:
                raise ScriptLockError(f"lockfile is too large: {path}")
            content = path.read_text(encoding="utf-8")
            if self.lock_matches_input(content, expected_input_digest):
                return ScriptLock(
                    source="sidecar",
                    content=content,
                    path=path,
                )
        return None

    def input_digest(
        self,
        metadata: ScriptMetadata | None,
        with_specs: list[str] | None = None,
        channels: list[str] | None = None,
    ) -> str:
        """Compute the dependency input digest stored in generated locks."""
        payload = {
            "channels": list(channels or []),
            "metadata": {
                "conda_channels": list(metadata.conda_channels) if metadata else [],
                "conda_dependencies": (
                    sorted(metadata.conda_dependencies) if metadata else []
                ),
                "pypi_dependencies": sorted(metadata.pypi_dependencies)
                if metadata
                else [],
                "requires_python": metadata.requires_python if metadata else None,
            },
            "with_specs": sorted(with_specs or []),
        }
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode()).hexdigest()

    def add_input_digest(self, lock_content: str, input_digest: str) -> str:
        """Prefix lock content with conda-exec input metadata."""
        return f"{LOCK_INPUT_DIGEST_PREFIX}{input_digest}\n{lock_content.rstrip()}\n"

    def read_input_digest(self, lock_content: str) -> str | None:
        """Read the conda-exec input digest from generated lock content."""
        for line in lock_content.splitlines()[:20]:
            if line.startswith(LOCK_INPUT_DIGEST_PREFIX):
                return line.removeprefix(LOCK_INPUT_DIGEST_PREFIX).strip()
        return None

    def lock_matches_input(
        self,
        lock_content: str,
        expected_input_digest: str | None,
    ) -> bool:
        """Return whether generated lock content matches current script input."""
        if expected_input_digest is None:
            return True
        return self.read_input_digest(lock_content) == expected_input_digest

    def write_sidecar(self, script_path: Path, lock_content: str) -> Path:
        """Write sidecar lock data using an atomic replace."""
        lock_path = self.default_sidecar_path(script_path)
        self.write_text_atomic(lock_path, lock_content)
        return lock_path

    def write_embedded(self, script_path: Path, lock_content: str) -> None:
        """Write or replace generated lock data embedded in a script."""
        if len(lock_content.encode("utf-8")) > MAX_LOCK_SIZE:
            raise ScriptLockError("embedded lock data is too large")

        original_mode = stat.S_IMODE(script_path.stat().st_mode)
        lines = script_path.read_text(encoding="utf-8").splitlines()
        lock_start = None
        lock_end = None
        for index, line in enumerate(lines):
            if line == LOCK_MARKER:
                lock_start = index
                continue
            if lock_start is not None and line == LOCK_END:
                lock_end = index
                break

        block = [LOCK_MARKER]
        block.extend(f"# {line}" if line else "#" for line in lock_content.splitlines())
        block.append(LOCK_END)

        if lock_start is not None and lock_end is not None:
            new_lines = [*lines[:lock_start], *block, *lines[lock_end + 1 :]]
        else:
            new_lines = [*block, "", *lines]
            for index, line in enumerate(lines):
                if line != "# /// script":
                    continue
                for end_index in range(index + 1, len(lines)):
                    if lines[end_index] == LOCK_END:
                        new_lines = [
                            *lines[: end_index + 1],
                            "",
                            *block,
                            *lines[end_index + 1 :],
                        ]
                        break
                break

        self.write_text_atomic(
            script_path,
            "\n".join(new_lines) + "\n",
            mode=original_mode,
        )

    def export_content(self, prefix: Path, platforms: list[str] | None = None) -> str:
        """Export a prefix to lockfile text using conda's exporter plugin."""
        exporter = self.exporter
        export_platforms = platforms or [context.subdir]
        unknown = set(export_platforms) - set(KNOWN_SUBDIRS)
        if unknown:
            raise ScriptLockError(
                f"unknown platform(s): {', '.join(sorted(unknown))}",
                hints=[f"valid platforms include: {', '.join(sorted(KNOWN_SUBDIRS))}"],
            )
        if len(export_platforms) > 1 and exporter.multiplatform_export is None:
            raise ScriptLockError(
                f"lock exporter {exporter.name!r} does not support multiple platforms"
            )

        try:
            environment = Environment.from_prefix(
                prefix=str(prefix),
                name=str(env_name(str(prefix)) or prefix.name),
                platform=context.subdir,
                from_history=False,
                no_builds=False,
                ignore_channels=False,
                channels=list(context.channels),
            )
            environments = [
                environment.extrapolate(platform) for platform in export_platforms
            ]
            if exporter.multiplatform_export is not None:
                return exporter.multiplatform_export(environments).rstrip() + "\n"
            if exporter.export is not None:
                return exporter.export(environments[0]).rstrip() + "\n"
        except CondaError as exc:
            raise ScriptLockError(f"failed to export lock data: {exc}") from exc

        raise ScriptLockError(f"lock exporter {exporter.name!r} does not define export")

    def create_environment(
        self,
        envs_dir: Path,
        final_prefix: Path,
        lock_content: str,
    ) -> Path:
        """Create a cached environment from lock data via temp prefix and rename."""
        envs_dir.mkdir(parents=True, exist_ok=True)
        tmp_prefix = Path(tempfile.mkdtemp(dir=envs_dir, prefix=".tmp-"))
        lock_path = tmp_prefix.with_suffix(f".{self.lock_format.default_filenames[0]}")
        try:
            self.write_text_atomic(lock_path, lock_content)
            args = [
                sys.executable,
                "-m",
                "conda",
                "create",
                "--yes",
                "--quiet",
                "--prefix",
                str(tmp_prefix),
                "--file",
                str(lock_path),
                "--environment-specifier",
                self.lock_format.name,
            ]
            result = subprocess.run(args, capture_output=True, text=True)  # noqa: S603
            if result.returncode:
                detail = (
                    result.stderr.strip()
                    or result.stdout.strip()
                    or f"exit code {result.returncode}"
                )
                raise ScriptLockError(
                    f"failed to create environment from lock data: {detail}",
                    hints=[
                        "install conda-lockfiles if this conda cannot read lockfiles"
                    ],
                )
            rename(str(tmp_prefix), str(final_prefix))
        except OSError:
            rm_rf(tmp_prefix)
            if final_prefix.is_dir() and (final_prefix / "conda-meta").is_dir():
                return final_prefix
            raise
        except BaseException:
            rm_rf(tmp_prefix)
            raise
        finally:
            if lock_path.exists():
                lock_path.unlink()
        return final_prefix

    def write_text_atomic(
        self,
        path: Path,
        content: str,
        mode: int | None = None,
    ) -> None:
        """Write text with tempfile and atomic replace."""
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                delete=False,
            ) as tmp:
                tmp_path = Path(tmp.name)
                tmp.write(content)
                tmp.flush()
                os.fsync(tmp.fileno())
            if mode is not None:
                tmp_path.chmod(mode)
            tmp_path.replace(path)
        finally:
            if tmp_path is not None and tmp_path.exists():
                tmp_path.unlink()

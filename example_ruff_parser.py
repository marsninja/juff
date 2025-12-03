"""
Small, self-contained Ruff configuration parser inspired by the reference Rust
implementation in `crates/ruff_workspace/src/pyproject.rs` and
`crates/ruff_workspace/src/configuration.rs`.

This module demonstrates:
- Discovery order: `.ruff.toml` > `ruff.toml` > `pyproject.toml` with
  `[tool.ruff]`.
- Parsing of the TOML payload into a minimal model (subset of Ruff's options).
- Support for `extend` chains with child values overriding parents and
  extend-style lists appended.
- Optional `target-version` fallback derived from `project.requires-python`
  when a discovered ancestor configuration omits it (mirroring the
  `RequiresPythonFallback` strategy in the Rust code).

The goal is to show the shape of Ruff's parsing and merge semantics without
pulling in any of the Rust code or wider Python project.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set
import os
import re
import sys

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - fallback for older Python
    import tomli as tomllib  # type: ignore


# --------- Data models --------- #


@dataclass
class RuleSelection:
    """Minimal representation of a single lint rule selection block."""

    select: Optional[List[str]] = None  # None means "inherit"
    ignore: List[str] = field(default_factory=list)
    extend_select: List[str] = field(default_factory=list)


@dataclass
class RuffConfig:
    """Subset of Ruff options relevant for this example parser."""

    path: Path
    extend: Optional[str] = None
    line_length: Optional[int] = None
    target_version: Optional[str] = None
    exclude: Optional[List[str]] = None
    extend_exclude: List[str] = field(default_factory=list)
    rule_selections: List[RuleSelection] = field(default_factory=list)
    per_file_ignores: Dict[str, List[str]] = field(default_factory=dict)

    def merge(self, parent: "RuffConfig") -> "RuffConfig":
        """
        Combine this configuration with a parent configuration following the
        same precedence as the Rust `Configuration::combine`:
        - Prefer child scalar values when set, otherwise inherit the parent.
        - Append extend-style lists (parent first, then child additions).
        - Concatenate rule selections so later entries (child) apply last.
        - For per-file-ignores, child entries override parent keys.
        """

        merged_per_file_ignores = dict(parent.per_file_ignores)
        merged_per_file_ignores.update(self.per_file_ignores)

        return RuffConfig(
            path=self.path,
            extend=None,  # We have already followed the chain.
            line_length=self.line_length or parent.line_length,
            target_version=self.target_version or parent.target_version,
            exclude=self.exclude or parent.exclude,
            extend_exclude=parent.extend_exclude + self.extend_exclude,
            rule_selections=parent.rule_selections + self.rule_selections,
            per_file_ignores=merged_per_file_ignores,
        )


# --------- TOML helpers --------- #


def load_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def find_settings_file(directory: Path) -> Optional[Path]:
    """
    Mirror the Rust `settings_toml` lookup:
    1) `.ruff.toml`
    2) `ruff.toml`
    3) `pyproject.toml` containing a `[tool.ruff]` table.
    """

    for name in (".ruff.toml", "ruff.toml"):
        candidate = directory / name
        if candidate.is_file():
            return candidate

    pyproject = directory / "pyproject.toml"
    if pyproject.is_file():
        data = load_toml(pyproject)
        tool = data.get("tool")
        if isinstance(tool, dict) and "ruff" in tool:
            return pyproject

    return None


def find_settings_in_ancestors(start: Path) -> Optional[Path]:
    """Walk ancestors until a Ruff configuration file is found."""

    for directory in start.resolve().absolute().parents:
        found = find_settings_file(directory)
        if found:
            return found
    return None


# --------- Normalization and parsing --------- #


def _warn_unknown_keys(source: Path, allowed: Iterable[str], actual: dict) -> None:
    unknown = set(actual).difference(allowed)
    if unknown:
        print(
            f"[warn] {source}: ignoring unknown keys {sorted(unknown)}",
            file=sys.stderr,
        )


def _derive_target_version_from_requires_python(
    spec: Optional[str],
) -> Optional[str]:
    """
    Approximate the Rust `get_minimum_supported_version` by pulling the lowest
    major.minor pair from a requires-python specifier string.
    """

    if not spec:
        return None

    versions = []
    for raw_part in spec.split(","):
        part = raw_part.strip()
        if not part:
            continue
        match = re.match(r"([><=~!]{1,2})\s*([0-9]+(?:\.[0-9]+)*)", part)
        if not match:
            continue
        op, version_text = match.groups()
        if op not in {"=", "==", ">=", ">", "~="}:
            continue
        components = version_text.split(".")
        if len(components) < 2:
            continue
        try:
            major, minor = int(components[0]), int(components[1])
        except ValueError:
            continue
        versions.append((major, minor))

    if not versions:
        return None

    major, minor = min(versions)
    # Ruff encodes targets like `py38`, `py310`, etc.
    return f"py{major}{minor}"


def _normalize_ruff_table(
    table: dict,
    path: Path,
    *,
    requires_python: Optional[str],
    allow_target_fallback: bool,
) -> RuffConfig:
    allowed_top_level = {
        "extend",
        "line-length",
        "target-version",
        "exclude",
        "extend-exclude",
        "lint",
    }
    _warn_unknown_keys(path, allowed_top_level, table)

    lint_table = table.get("lint") or {}
    if isinstance(lint_table, dict):
        allowed_lint = {"select", "ignore", "extend-select", "per-file-ignores"}
        _warn_unknown_keys(path, allowed_lint, lint_table)
    else:
        lint_table = {}

    selection = RuleSelection(
        select=lint_table.get("select") if "select" in lint_table else None,
        ignore=list(lint_table.get("ignore", [])),
        extend_select=list(lint_table.get("extend-select", [])),
    )

    target_version = table.get("target-version")
    if not target_version and allow_target_fallback:
        target_version = _derive_target_version_from_requires_python(requires_python)

    return RuffConfig(
        path=path,
        extend=table.get("extend"),
        line_length=table.get("line-length"),
        target_version=target_version,
        exclude=table.get("exclude"),
        extend_exclude=list(table.get("extend-exclude", [])),
        rule_selections=[selection],
        per_file_ignores=dict(lint_table.get("per-file-ignores", {})),
    )


def load_single_config(path: Path, *, allow_target_fallback: bool) -> RuffConfig:
    """
    Load a single configuration file without following `extend`. For
    `pyproject.toml`, only the `[tool.ruff]` table is considered.
    """

    data = load_toml(path)
    requires_python = None
    table: dict

    if path.name == "pyproject.toml":
        table = data.get("tool", {}).get("ruff")
        if table is None:
            raise ValueError(f"{path} does not contain [tool.ruff]")
        requires_python = data.get("project", {}).get("requires-python")
    else:
        table = data
        if allow_target_fallback:
            sibling = path.parent / "pyproject.toml"
            if sibling.is_file():
                requires_python = load_toml(sibling).get("project", {}).get(
                    "requires-python"
                )

    return _normalize_ruff_table(
        table,
        path,
        requires_python=requires_python,
        allow_target_fallback=allow_target_fallback,
    )


def resolve_with_extends(start: Path, *, infer_target_version: bool = True) -> RuffConfig:
    """
    Follow the `extend` chain starting at `start`, mirroring the Rust
    `resolve_configuration` loop. The first configuration may derive its target
    version from `requires-python`; extended configs do not.
    """

    seen: Set[Path] = set()
    configs: List[RuffConfig] = []
    path: Optional[Path] = start
    allow_fallback = infer_target_version

    while path:
        normalized = path.resolve()
        if normalized in seen:
            chain = " -> ".join(str(p) for p in configs)
            raise ValueError(f"Circular configuration detected: {chain} -> {path}")
        seen.add(normalized)

        cfg = load_single_config(normalized, allow_target_fallback=allow_fallback)
        configs.append(cfg)

        if cfg.extend:
            next_path = Path(os.path.expanduser(os.path.expandvars(cfg.extend)))
            if not next_path.is_absolute():
                next_path = (normalized.parent / next_path).resolve()
            path = next_path
        else:
            path = None
        allow_fallback = False  # Only the first hop gets the fallback behavior.

    merged = configs[0]
    for parent in configs[1:]:
        merged = merged.merge(parent)
    return merged


# --------- Rule resolution (simplified) --------- #


def materialize_rules(config: RuffConfig) -> Set[str]:
    """
    Collapse rule selections into a concrete set, using a simplified version of
    the Rust `as_rule_table` logic:
    - Start with Ruff's defaults (E/F) to match DEFAULT_SELECTORS.
    - A non-null `select` replaces the active set.
    - `extend-select` adds rules.
    - `ignore` removes rules.
    """

    active: Set[str] = {"E", "F"}
    for selection in config.rule_selections:
        if selection.select is not None:
            active = set(selection.select)
        active.update(selection.extend_select)
        active.difference_update(selection.ignore)
    return active


# --------- CLI demo --------- #


def _human_report(config: RuffConfig) -> str:
    rules = ", ".join(sorted(materialize_rules(config)))
    lines = [
        f"Config path: {config.path}",
        f"  line-length: {config.line_length or 'default'}",
        f"  target-version: {config.target_version or 'default'}",
        f"  exclude: {config.exclude or []}",
        f"  extend-exclude: {config.extend_exclude}",
        f"  per-file-ignores: {config.per_file_ignores}",
        f"  resolved rules: {rules}",
    ]
    return "\n".join(lines)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Example Ruff configuration parser.")
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to a configuration file or a directory containing one.",
    )
    args = parser.parse_args()

    target = Path(args.path)
    if target.is_dir():
        settings = find_settings_file(target) or find_settings_in_ancestors(target)
        if not settings:
            raise SystemExit(f"No Ruff config found under {target}")
    else:
        settings = target

    config = resolve_with_extends(settings)
    print(_human_report(config))


if __name__ == "__main__":
    main()

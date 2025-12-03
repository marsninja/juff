"""Configuration parser for Juff.

This module handles parsing of juff.toml configuration files, providing
compatibility with ruff.toml format while using the juff.toml filename.
"""

import fnmatch
import sys
from pathlib import Path
from typing import Any, Optional

import tomllib


# Mapping of ruff rule prefixes to their corresponding tools
# Organized by tool type: flake8 plugins, standalone linters, formatters, ruff-only
RULE_PREFIX_MAPPING = {
    # === Core flake8 (pycodestyle, pyflakes, mccabe) ===
    "E": "flake8",  # pycodestyle errors
    "W": "flake8",  # pycodestyle warnings
    "F": "flake8",  # pyflakes
    "C90": "flake8",  # mccabe complexity
    # === flake8 plugins (alphabetical by prefix) ===
    "A": "flake8",  # flake8-builtins
    "ANN": "flake8",  # flake8-annotations
    "ARG": "flake8",  # flake8-unused-arguments
    "ASYNC": "flake8",  # flake8-async
    "B": "flake8",  # flake8-bugbear
    "BLE": "flake8",  # flake8-blind-except
    "C4": "flake8",  # flake8-comprehensions
    "COM": "flake8",  # flake8-commas
    "CPY": "flake8",  # flake8-copyright
    "D": "flake8",  # flake8-docstrings (pydocstyle)
    "DJ": "flake8",  # flake8-django
    "DTZ": "flake8",  # flake8-datetimez
    "EM": "flake8",  # flake8-errmsg
    "ERA": "flake8",  # flake8-eradicate
    "EXE": "flake8",  # flake8-executable
    "FA": "flake8",  # flake8-future-annotations
    "FBT": "flake8",  # flake8-boolean-trap
    "FIX": "flake8",  # flake8-fixme
    "G": "flake8",  # flake8-logging-format
    "ICN": "flake8",  # flake8-import-conventions
    "INP": "flake8",  # flake8-no-pep420
    "INT": "flake8",  # flake8-gettext
    "ISC": "flake8",  # flake8-implicit-str-concat
    "LOG": "flake8",  # flake8-logging
    "N": "flake8",  # pep8-naming
    "PD": "flake8",  # pandas-vet
    "PIE": "flake8",  # flake8-pie
    "PT": "flake8",  # flake8-pytest-style
    "PTH": "flake8",  # flake8-use-pathlib
    "PYI": "flake8",  # flake8-pyi
    "Q": "flake8",  # flake8-quotes
    "RET": "flake8",  # flake8-return
    "RSE": "flake8",  # flake8-raise
    "S": "flake8",  # flake8-bandit
    "SIM": "flake8",  # flake8-simplify
    "SLF": "flake8",  # flake8-self
    "SLOT": "flake8",  # flake8-slots
    "T10": "flake8",  # flake8-debugger
    "T20": "flake8",  # flake8-print
    "TCH": "flake8",  # flake8-type-checking
    "TD": "flake8",  # flake8-todos
    "TID": "flake8",  # flake8-tidy-imports
    "TRY": "flake8",  # tryceratops (flake8 plugin)
    "YTT": "flake8",  # flake8-2020
    # === Standalone linters ===
    "DOC": "pydoclint",  # pydoclint
    "FURB": "refurb",  # refurb
    "PERF": "perflint",  # perflint
    "PLC": "pylint",  # pylint Convention
    "PLE": "pylint",  # pylint Error
    "PLR": "pylint",  # pylint Refactor
    "PLW": "pylint",  # pylint Warning
    # === Formatters and code upgraders ===
    "I": "isort",  # isort
    "UP": "pyupgrade",  # pyupgrade
    "FLY": "flynt",  # flynt (f-string conversion)
    "format": "black",  # black formatting
    # === Ruff-only rules (delegated to ruff) ===
    "AIR": "ruff",  # Airflow rules
    "FAST": "ruff",  # FastAPI rules
    "NPY": "ruff",  # NumPy rules
    "PGH": "ruff",  # pygrep-hooks
    "RUF": "ruff",  # Ruff-specific rules
}

# Rule prefixes that are handled by ruff (no Python equivalent)
RUFF_ONLY_PREFIXES = {"AIR", "FAST", "NPY", "PGH", "RUF"}

# Config file search order
CONFIG_FILES = [
    "juff.toml",
    ".juff.toml",
    "pyproject.toml",
]


class JuffConfig:
    """Configuration manager for Juff."""

    def __init__(self, config_path: Path | None = None):
        """Initialize the configuration.

        Args:
            config_path: Optional explicit path to config file.
        """
        self.config_path = config_path
        self._config: dict[str, Any] | None = None

    def find_config_file(self, start_dir: Path | None = None) -> Path | None:
        """Find a config file by walking up the directory tree.

        Args:
            start_dir: Directory to start searching from. Defaults to cwd.

        Returns:
            Path to config file if found, None otherwise.
        """
        if self.config_path is not None:
            return self.config_path if self.config_path.exists() else None

        if start_dir is None:
            start_dir = Path.cwd()

        current = start_dir.resolve()
        while True:
            for config_name in CONFIG_FILES:
                config_file = current / config_name
                if config_file.exists():
                    # For pyproject.toml, check if it has [tool.juff] section
                    if config_name == "pyproject.toml":
                        try:
                            with open(config_file, "rb") as f:
                                data = tomllib.load(f)
                            if "tool" in data and "juff" in data["tool"]:
                                return config_file
                        except Exception:
                            continue
                    else:
                        return config_file

            parent = current.parent
            if parent == current:
                break
            current = parent

        return None

    def load(self, start_dir: Path | None = None) -> dict[str, Any]:
        """Load the configuration.

        Args:
            start_dir: Directory to start searching for config.

        Returns:
            Configuration dictionary.
        """
        if self._config is not None:
            return self._config

        config_file = self.find_config_file(start_dir)
        if config_file is None:
            self._config = {}
            return self._config

        with open(config_file, "rb") as f:
            data = tomllib.load(f)

        # Handle pyproject.toml vs juff.toml
        if config_file.name == "pyproject.toml":
            self._config = data.get("tool", {}).get("juff", {})
        else:
            self._config = data

        self.config_path = config_file
        return self._config

    @property
    def config(self) -> dict[str, Any]:
        """Get the loaded configuration."""
        if self._config is None:
            return self.load()
        return self._config

    def get_lint_config(self) -> dict[str, Any]:
        """Get lint-specific configuration."""
        return self.config.get("lint", {})

    def get_format_config(self) -> dict[str, Any]:
        """Get format-specific configuration."""
        return self.config.get("format", {})

    def get_selected_rules(self) -> list[str]:
        """Get the list of selected lint rules."""
        lint_config = self.get_lint_config()
        return lint_config.get("select", ["E", "F", "W"])

    def get_ignored_rules(self) -> list[str]:
        """Get the list of ignored lint rules."""
        lint_config = self.get_lint_config()
        return lint_config.get("ignore", [])

    def get_line_length(self) -> int:
        """Get the configured line length."""
        return self.config.get("line-length", 88)

    def get_target_version(self) -> str:
        """Get the target Python version."""
        return self.config.get("target-version", "py311")

    def get_exclude_patterns(self, mode: str | None = None) -> list[str]:
        """Get file/directory exclusion patterns.

        Args:
            mode: Optional mode ('lint' or 'format') to include section-specific excludes.

        Returns:
            List of exclusion patterns (root-level + section-specific if mode provided).
        """
        # Start with root-level excludes
        patterns = list(self.config.get("exclude", []))

        # Add section-specific excludes if mode is specified
        if mode == "lint":
            lint_excludes = self.get_lint_config().get("exclude", [])
            patterns.extend(lint_excludes)
        elif mode == "format":
            format_excludes = self.get_format_config().get("exclude", [])
            patterns.extend(format_excludes)

        return patterns

    def get_include_patterns(self) -> list[str]:
        """Get file/directory inclusion patterns."""
        return self.config.get("include", ["*.py"])

    def get_fixable_rules(self) -> list[str]:
        """Get rules that are auto-fixable."""
        lint_config = self.get_lint_config()
        return lint_config.get("fixable", ["ALL"])

    def get_unfixable_rules(self) -> list[str]:
        """Get rules that should not be auto-fixed."""
        lint_config = self.get_lint_config()
        return lint_config.get("unfixable", [])

    def is_rule_selected(self, rule: str) -> bool:
        """Check if a rule is selected for linting.

        Args:
            rule: Rule code (e.g., 'E501', 'F401').

        Returns:
            True if the rule should be checked.
        """
        selected = self.get_selected_rules()
        ignored = self.get_ignored_rules()

        # Check if explicitly ignored
        if rule in ignored:
            return False

        # Check if rule or its prefix is selected
        for sel in selected:
            if sel == "ALL" or rule.startswith(sel):
                return True

        return False

    def get_tools_for_rules(self) -> set[str]:
        """Get the set of tools needed for selected rules.

        Returns:
            Set of tool names (e.g., {'flake8', 'isort', 'black'}).
        """
        selected = self.get_selected_rules()
        tools = set()

        for rule in selected:
            if rule == "ALL":
                tools.update(RULE_PREFIX_MAPPING.values())
                break

            # Find matching prefix
            for prefix, tool in RULE_PREFIX_MAPPING.items():
                if rule == prefix or rule.startswith(prefix):
                    tools.add(tool)
                    break

        return tools

    # ========== Per-file ignores ==========

    def get_per_file_ignores(self) -> dict[str, list[str]]:
        """Get per-file ignore patterns.

        Returns:
            Dictionary mapping file patterns to lists of ignored rules.
        """
        lint_config = self.get_lint_config()
        return lint_config.get("per-file-ignores", {})

    def get_ignored_rules_for_file(self, file_path: Path) -> list[str]:
        """Get the list of ignored rules for a specific file.

        Args:
            file_path: Path to the file to check.

        Returns:
            List of rule codes to ignore for this file.
        """
        per_file_ignores = self.get_per_file_ignores()
        global_ignores = self.get_ignored_rules()
        ignored = list(global_ignores)

        # Convert to string for pattern matching
        file_str = str(file_path)

        for pattern, rules in per_file_ignores.items():
            # Handle glob patterns like "**/tests/*" or "src/*.py"
            if self._matches_pattern(file_str, pattern):
                ignored.extend(rules)

        return ignored

    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if a file path matches a glob pattern.

        Args:
            file_path: The file path to check.
            pattern: The glob pattern (supports ** for recursive).

        Returns:
            True if the path matches the pattern.
        """
        # Normalize path separators
        file_path = file_path.replace("\\", "/")
        pattern = pattern.replace("\\", "/")

        # Handle ** patterns (recursive matching)
        if "**" in pattern:
            # Convert ** pattern to work with fnmatch
            # e.g., "**/tests/*" should match "foo/tests/bar.py"
            parts = pattern.split("**")
            if len(parts) == 2:
                prefix, suffix = parts
                # Check if any part of the path matches
                if prefix and not file_path.startswith(prefix.rstrip("/")):
                    # Check if prefix appears anywhere in path
                    pass
                if suffix:
                    suffix = suffix.lstrip("/")
                    # Check if the suffix pattern matches
                    path_parts = file_path.split("/")
                    for i in range(len(path_parts)):
                        remaining = "/".join(path_parts[i:])
                        if fnmatch.fnmatch(remaining, suffix + "*") or fnmatch.fnmatch(
                            remaining, "*/" + suffix + "*"
                        ):
                            return True
                        if fnmatch.fnmatch(remaining, suffix):
                            return True
                else:
                    return True
            return fnmatch.fnmatch(file_path, pattern.replace("**", "*"))

        return fnmatch.fnmatch(file_path, pattern)

    def is_file_excluded(self, file_path: Path, mode: str | None = None) -> bool:
        """Check if a file should be excluded from processing.

        Args:
            file_path: Path to the file to check.
            mode: Optional mode ('lint' or 'format') to include section-specific excludes.

        Returns:
            True if the file should be excluded.
        """
        exclude_patterns = self.get_exclude_patterns(mode=mode)
        file_str = str(file_path).replace("\\", "/")

        for pattern in exclude_patterns:
            if self._matches_pattern(file_str, pattern):
                return True
            # Also check if any path component matches
            pattern_normalized = pattern.rstrip("/")
            if pattern_normalized in file_str:
                return True

        return False

    def is_rule_ignored_for_file(self, rule: str, file_path: Path) -> bool:
        """Check if a rule is ignored for a specific file.

        Args:
            rule: Rule code (e.g., 'E501', 'ANN').
            file_path: Path to the file.

        Returns:
            True if the rule should be ignored for this file.
        """
        ignored = self.get_ignored_rules_for_file(file_path)

        for ignore in ignored:
            if ignore == "ALL":
                return True
            if rule == ignore or rule.startswith(ignore):
                return True

        return False

    # ========== Tool-specific configurations ==========

    def get_isort_config(self) -> dict[str, Any]:
        """Get isort-specific configuration from [lint.isort].

        Returns:
            Dictionary of isort configuration options.
        """
        lint_config = self.get_lint_config()
        return lint_config.get("isort", {})

    def get_isort_known_first_party(self) -> list[str]:
        """Get known first-party packages for isort.

        Returns:
            List of first-party package names.
        """
        isort_config = self.get_isort_config()
        return isort_config.get("known-first-party", [])

    def get_isort_known_third_party(self) -> list[str]:
        """Get known third-party packages for isort.

        Returns:
            List of third-party package names.
        """
        isort_config = self.get_isort_config()
        return isort_config.get("known-third-party", [])

    def get_flake8_annotations_config(self) -> dict[str, Any]:
        """Get flake8-annotations configuration from [lint.flake8-annotations].

        Returns:
            Dictionary of flake8-annotations configuration options.
        """
        lint_config = self.get_lint_config()
        return lint_config.get("flake8-annotations", {})

    def get_flake8_annotations_suppress_none_returning(self) -> bool:
        """Get suppress-none-returning option for flake8-annotations.

        Returns:
            True if None-returning functions should not require annotation.
        """
        ann_config = self.get_flake8_annotations_config()
        return ann_config.get("suppress-none-returning", False)

    def get_flake8_quotes_config(self) -> dict[str, Any]:
        """Get flake8-quotes configuration from [lint.flake8-quotes].

        Returns:
            Dictionary of flake8-quotes configuration options.
        """
        lint_config = self.get_lint_config()
        return lint_config.get("flake8-quotes", {})

    def get_pydocstyle_config(self) -> dict[str, Any]:
        """Get pydocstyle configuration from [lint.pydocstyle].

        Returns:
            Dictionary of pydocstyle configuration options.
        """
        lint_config = self.get_lint_config()
        return lint_config.get("pydocstyle", {})

    def get_mccabe_config(self) -> dict[str, Any]:
        """Get mccabe configuration from [lint.mccabe].

        Returns:
            Dictionary of mccabe configuration options.
        """
        lint_config = self.get_lint_config()
        return lint_config.get("mccabe", {})

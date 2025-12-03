"""Configuration parser for Juff.

This module handles parsing of juff.toml configuration files, providing
compatibility with ruff.toml format while using the juff.toml filename.
"""

import fnmatch
import sys
from pathlib import Path
from typing import Any, Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


# Mapping of ruff rule prefixes to their corresponding flake8 plugins/tools
RULE_PREFIX_MAPPING = {
    # pycodestyle
    "E": "flake8",  # Error
    "W": "flake8",  # Warning
    # Pyflakes
    "F": "flake8",
    # flake8-bugbear
    "B": "flake8-bugbear",
    # flake8-comprehensions
    "C4": "flake8-comprehensions",
    # flake8-simplify
    "SIM": "flake8-simplify",
    # flake8-pie
    "PIE": "flake8-pie",
    # flake8-bandit (security)
    "S": "flake8-bandit",
    # flake8-builtins
    "A": "flake8-builtins",
    # flake8-commas
    "COM": "flake8-commas",
    # flake8-debugger
    "T10": "flake8-debugger",
    # pydocstyle / flake8-docstrings
    "D": "flake8-docstrings",
    # flake8-eradicate
    "ERA": "flake8-eradicate",
    # flake8-executable
    "EXE": "flake8-executable",
    # flake8-implicit-str-concat
    "ISC": "flake8-implicit-str-concat",
    # flake8-logging-format
    "G": "flake8-logging-format",
    # flake8-no-pep420
    "INP": "flake8-no-pep420",
    # flake8-print
    "T20": "flake8-print",
    # flake8-pytest-style
    "PT": "flake8-pytest-style",
    # flake8-quotes
    "Q": "flake8-quotes",
    # flake8-return
    "RET": "flake8-return",
    # flake8-self
    "SLF": "flake8-self",
    # flake8-tidy-imports
    "TID": "flake8-tidy-imports",
    # flake8-type-checking
    "TCH": "flake8-type-checking",
    # flake8-use-pathlib
    "PTH": "flake8-use-pathlib",
    # pep8-naming
    "N": "pep8-naming",
    # flake8-annotations
    "ANN": "flake8-annotations",
    # flake8-async
    "ASYNC": "flake8-async",
    # flake8-blind-except
    "BLE": "flake8-blind-except",
    # flake8-boolean-trap
    "FBT": "flake8-boolean-trap",
    # flake8-raise
    "RSE": "flake8-raise",
    # flake8-slots
    "SLOT": "flake8-slots",
    # flake8-gettext
    "INT": "flake8-gettext",
    # tryceratops
    "TRY": "tryceratops",
    # flake8-unused-arguments
    "ARG": "flake8-unused-arguments",
    # flake8-datetimez
    "DTZ": "flake8-datetimez",
    # flake8-errmsg
    "EM": "flake8-errmsg",
    # flake8-future-annotations
    "FA": "flake8-future-annotations",
    # isort
    "I": "isort",
    # pyupgrade
    "UP": "pyupgrade",
    # Black (formatting)
    "format": "black",
}

# Config file search order
CONFIG_FILES = [
    "juff.toml",
    ".juff.toml",
    "pyproject.toml",
]


class JuffConfig:
    """Configuration manager for Juff."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the configuration.

        Args:
            config_path: Optional explicit path to config file.
        """
        self.config_path = config_path
        self._config: Optional[dict[str, Any]] = None

    def find_config_file(self, start_dir: Optional[Path] = None) -> Optional[Path]:
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

    def load(self, start_dir: Optional[Path] = None) -> dict[str, Any]:
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

    def get_exclude_patterns(self) -> list[str]:
        """Get file/directory exclusion patterns."""
        return self.config.get("exclude", [])

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

    def is_file_excluded(self, file_path: Path) -> bool:
        """Check if a file should be excluded from processing.

        Args:
            file_path: Path to the file to check.

        Returns:
            True if the file should be excluded.
        """
        exclude_patterns = self.get_exclude_patterns()
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

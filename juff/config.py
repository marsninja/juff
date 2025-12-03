"""Configuration parser for Juff.

This module handles parsing of juff.toml configuration files, providing
full compatibility with ruff.toml format while using the juff.toml filename.
Supports all ruff configuration options for seamless migration.
"""

import fnmatch
from pathlib import Path
from typing import Any

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

# Config file search order (supports both juff and ruff configs for migration)
CONFIG_FILES = [
    "juff.toml",
    ".juff.toml",
    "ruff.toml",
    ".ruff.toml",
    "pyproject.toml",
]

# Default exclusion patterns (same as ruff)
DEFAULT_EXCLUDE = [
    ".bzr",
    ".direnv",
    ".eggs",
    ".git",
    ".git-rewrite",
    ".hg",
    ".mypy_cache",
    ".nox",
    ".pants.d",
    ".pytype",
    ".ruff_cache",
    ".juff_cache",
    ".svn",
    ".tox",
    ".venv",
    "__pycache__",
    "__pypackages__",
    "_build",
    "buck-out",
    "dist",
    "node_modules",
    "venv",
]

# Default inclusion patterns
DEFAULT_INCLUDE = ["*.py", "*.pyi", "*.pyw"]


class JuffConfig:
    """Configuration manager for Juff.

    Fully compatible with ruff.toml configuration format. Supports all ruff
    configuration options for lint, format, and global settings.
    """

    def __init__(self, config_path: Path | None = None):
        """Initialize the configuration.

        Args:
            config_path: Optional explicit path to config file.
        """
        self.config_path = config_path
        self._config: dict[str, Any] | None = None
        self._project_root: Path | None = None

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
                    # For pyproject.toml, check if it has [tool.juff] or [tool.ruff]
                    if config_name == "pyproject.toml":
                        try:
                            with open(config_file, "rb") as f:
                                data = tomllib.load(f)
                            tool = data.get("tool", {})
                            if "juff" in tool or "ruff" in tool:
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
            self._project_root = Path.cwd()
            return self._config

        self._project_root = config_file.parent

        with open(config_file, "rb") as f:
            data = tomllib.load(f)

        # Handle pyproject.toml vs juff.toml/ruff.toml
        if config_file.name == "pyproject.toml":
            tool = data.get("tool", {})
            # Prefer [tool.juff] over [tool.ruff]
            self._config = tool.get("juff", tool.get("ruff", {}))
        else:
            self._config = data

        # Handle extend configuration
        if "extend" in self._config:
            self._config = self._resolve_extend(self._config)

        self.config_path = config_file
        return self._config

    def _resolve_extend(
        self, config: dict[str, Any], seen_paths: set[Path] | None = None
    ) -> dict[str, Any]:
        """Resolve extend configuration by merging parent config.

        Supports recursive extends (grandparent -> parent -> child).

        Args:
            config: Current configuration with 'extend' key.
            seen_paths: Set of already-processed paths to detect cycles.

        Returns:
            Merged configuration.
        """
        extend_path = config.get("extend")
        if not extend_path:
            return config

        # Expand path
        extend_path = Path(extend_path).expanduser()
        if not extend_path.is_absolute() and self._project_root:
            extend_path = self._project_root / extend_path

        extend_path = extend_path.resolve()

        if not extend_path.exists():
            return config

        # Detect circular extends
        if seen_paths is None:
            seen_paths = set()
        if extend_path in seen_paths:
            return config  # Break cycle
        seen_paths.add(extend_path)

        # Load parent config
        with open(extend_path, "rb") as f:
            parent_data = tomllib.load(f)

        if extend_path.name == "pyproject.toml":
            tool = parent_data.get("tool", {})
            parent_config = tool.get("juff", tool.get("ruff", {}))
        else:
            parent_config = parent_data

        # Recursively resolve parent's extends (with parent's directory as root)
        old_root = self._project_root
        self._project_root = extend_path.parent
        parent_config = self._resolve_extend(parent_config, seen_paths)
        self._project_root = old_root

        # Merge: child overrides parent
        return self._merge_configs(parent_config, config)

    def _merge_configs(
        self, parent: dict[str, Any], child: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge parent and child configurations.

        Args:
            parent: Parent configuration.
            child: Child configuration (takes precedence).

        Returns:
            Merged configuration.
        """
        result = dict(parent)

        for key, value in child.items():
            if key == "extend":
                continue  # Don't copy extend key

            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    @property
    def config(self) -> dict[str, Any]:
        """Get the loaded configuration."""
        if self._config is None:
            return self.load()
        return self._config

    @property
    def project_root(self) -> Path:
        """Get the project root directory."""
        if self._project_root is None:
            self.load()
        return self._project_root or Path.cwd()

    # ========== Global Options ==========

    def get_cache_dir(self) -> Path:
        """Get the cache directory path."""
        cache_dir = self.config.get("cache-dir", ".juff_cache")
        path = Path(cache_dir).expanduser()
        if not path.is_absolute():
            path = self.project_root / path
        return path

    def get_output_format(self) -> str:
        """Get the output format for violations."""
        return self.config.get("output-format", "full")

    def is_fix_enabled(self) -> bool:
        """Check if fix mode is enabled by default."""
        return self.config.get("fix", False)

    def is_unsafe_fixes_enabled(self) -> bool | None:
        """Check if unsafe fixes are enabled."""
        return self.config.get("unsafe-fixes")

    def is_fix_only(self) -> bool:
        """Check if fix-only mode is enabled."""
        return self.config.get("fix-only", False)

    def is_show_fixes_enabled(self) -> bool:
        """Check if showing fixes is enabled."""
        return self.config.get("show-fixes", False)

    def get_required_version(self) -> str | None:
        """Get the required juff version."""
        return self.config.get("required-version")

    def is_preview_enabled(self) -> bool:
        """Check if preview mode is enabled."""
        return self.config.get("preview", False)

    def get_line_length(self) -> int:
        """Get the configured line length."""
        return self.config.get("line-length", 88)

    def get_indent_width(self) -> int:
        """Get the configured indent width."""
        return self.config.get("indent-width", 4)

    def get_target_version(self) -> str:
        """Get the target Python version."""
        return self.config.get("target-version", "py311")

    def get_per_file_target_version(self) -> dict[str, str]:
        """Get per-file target version overrides."""
        return self.config.get("per-file-target-version", {})

    def get_src_paths(self) -> list[str]:
        """Get the source directories for import resolution."""
        return self.config.get("src", [".", "src"])

    def get_builtins(self) -> list[str]:
        """Get additional builtins to treat as defined."""
        return self.config.get("builtins", [])

    def get_namespace_packages(self) -> list[str]:
        """Get directories to treat as namespace packages."""
        return self.config.get("namespace-packages", [])

    def is_respect_gitignore(self) -> bool:
        """Check if .gitignore should be respected."""
        return self.config.get("respect-gitignore", True)

    def is_force_exclude(self) -> bool:
        """Check if exclusions should be enforced for explicit paths."""
        return self.config.get("force-exclude", False)

    # ========== File Patterns ==========

    def get_exclude_patterns(self, mode: str | None = None) -> list[str]:
        """Get file/directory exclusion patterns.

        Args:
            mode: Optional mode ('lint' or 'format') for section-specific excludes.

        Returns:
            List of exclusion patterns.
        """
        # Start with configured or default excludes
        patterns = list(self.config.get("exclude", DEFAULT_EXCLUDE))

        # Add extend-exclude patterns
        patterns.extend(self.config.get("extend-exclude", []))

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
        patterns = list(self.config.get("include", DEFAULT_INCLUDE))
        patterns.extend(self.config.get("extend-include", []))
        return patterns

    # ========== Lint Configuration [lint] ==========

    def get_lint_config(self) -> dict[str, Any]:
        """Get lint-specific configuration."""
        return self.config.get("lint", {})

    def get_selected_rules(self) -> list[str]:
        """Get the list of selected lint rules."""
        lint_config = self.get_lint_config()

        # Check for select in lint section first
        if "select" in lint_config:
            rules = list(lint_config["select"])
        else:
            # Default to E, F, W if not specified
            rules = ["E", "F", "W"]

        # Add extend-select rules
        rules.extend(lint_config.get("extend-select", []))

        return rules

    def get_ignored_rules(self) -> list[str]:
        """Get the list of ignored lint rules."""
        lint_config = self.get_lint_config()
        ignored = list(lint_config.get("ignore", []))
        # Note: extend-ignore is deprecated but still supported
        ignored.extend(lint_config.get("extend-ignore", []))
        return ignored

    def get_fixable_rules(self) -> list[str]:
        """Get rules that are auto-fixable."""
        lint_config = self.get_lint_config()
        fixable = list(lint_config.get("fixable", ["ALL"]))
        fixable.extend(lint_config.get("extend-fixable", []))
        return fixable

    def get_unfixable_rules(self) -> list[str]:
        """Get rules that should not be auto-fixed."""
        lint_config = self.get_lint_config()
        unfixable = list(lint_config.get("unfixable", []))
        unfixable.extend(lint_config.get("extend-unfixable", []))
        return unfixable

    def get_safe_fixes(self) -> list[str]:
        """Get rules with extended safe fix behavior."""
        lint_config = self.get_lint_config()
        return lint_config.get("extend-safe-fixes", [])

    def get_unsafe_fixes(self) -> list[str]:
        """Get rules with extended unsafe fix behavior."""
        lint_config = self.get_lint_config()
        return lint_config.get("extend-unsafe-fixes", [])

    def is_lint_preview_enabled(self) -> bool:
        """Check if preview mode is enabled for linting."""
        lint_config = self.get_lint_config()
        return lint_config.get("preview", self.is_preview_enabled())

    def is_explicit_preview_rules(self) -> bool:
        """Check if preview rules require explicit selection."""
        lint_config = self.get_lint_config()
        return lint_config.get("explicit-preview-rules", False)

    def get_allowed_confusables(self) -> list[str]:
        """Get allowed confusable characters."""
        lint_config = self.get_lint_config()
        return lint_config.get("allowed-confusables", [])

    def get_dummy_variable_rgx(self) -> str | None:
        """Get the regex pattern for dummy variables."""
        lint_config = self.get_lint_config()
        return lint_config.get("dummy-variable-rgx")

    def get_external_rules(self) -> list[str]:
        """Get external rule codes to preserve."""
        lint_config = self.get_lint_config()
        return lint_config.get("external", [])

    def get_logger_objects(self) -> list[str]:
        """Get custom logger objects."""
        lint_config = self.get_lint_config()
        return lint_config.get("logger-objects", [])

    def get_task_tags(self) -> list[str]:
        """Get task comment tags (TODO, FIXME, etc.)."""
        lint_config = self.get_lint_config()
        return lint_config.get("task-tags", ["TODO", "FIXME", "XXX"])

    def get_typing_modules(self) -> list[str]:
        """Get additional typing modules."""
        lint_config = self.get_lint_config()
        return lint_config.get("typing-modules", [])

    # ========== Per-file Ignores ==========

    def get_per_file_ignores(self) -> dict[str, list[str]]:
        """Get per-file ignore patterns."""
        lint_config = self.get_lint_config()
        ignores = dict(lint_config.get("per-file-ignores", {}))

        # Merge extend-per-file-ignores
        for pattern, rules in lint_config.get("extend-per-file-ignores", {}).items():
            if pattern in ignores:
                ignores[pattern].extend(rules)
            else:
                ignores[pattern] = list(rules)

        return ignores

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

        file_str = str(file_path)

        for pattern, rules in per_file_ignores.items():
            if self._matches_pattern(file_str, pattern):
                ignored.extend(rules)

        return ignored

    # ========== Format Configuration [format] ==========

    def get_format_config(self) -> dict[str, Any]:
        """Get format-specific configuration."""
        return self.config.get("format", {})

    def get_format_indent_style(self) -> str:
        """Get the indent style for formatting (space or tab)."""
        format_config = self.get_format_config()
        return format_config.get("indent-style", "space")

    def get_format_quote_style(self) -> str:
        """Get the quote style for formatting."""
        format_config = self.get_format_config()
        return format_config.get("quote-style", "double")

    def get_format_line_ending(self) -> str:
        """Get the line ending style."""
        format_config = self.get_format_config()
        return format_config.get("line-ending", "auto")

    def is_skip_magic_trailing_comma(self) -> bool:
        """Check if magic trailing comma should be skipped."""
        format_config = self.get_format_config()
        return format_config.get("skip-magic-trailing-comma", False)

    def is_docstring_code_format(self) -> bool:
        """Check if code in docstrings should be formatted."""
        format_config = self.get_format_config()
        return format_config.get("docstring-code-format", False)

    def get_docstring_code_line_length(self) -> int | str:
        """Get the line length for docstring code blocks."""
        format_config = self.get_format_config()
        return format_config.get("docstring-code-line-length", "dynamic")

    def is_format_preview_enabled(self) -> bool:
        """Check if preview mode is enabled for formatting."""
        format_config = self.get_format_config()
        return format_config.get("preview", self.is_preview_enabled())

    # ========== Plugin Configurations [lint.xxx] ==========

    def get_isort_config(self) -> dict[str, Any]:
        """Get isort-specific configuration from [lint.isort]."""
        lint_config = self.get_lint_config()
        return lint_config.get("isort", {})

    def get_isort_known_first_party(self) -> list[str]:
        """Get known first-party packages for isort."""
        isort_config = self.get_isort_config()
        return isort_config.get("known-first-party", [])

    def get_isort_known_third_party(self) -> list[str]:
        """Get known third-party packages for isort."""
        isort_config = self.get_isort_config()
        return isort_config.get("known-third-party", [])

    def get_isort_known_local_folder(self) -> list[str]:
        """Get known local folder packages for isort."""
        isort_config = self.get_isort_config()
        return isort_config.get("known-local-folder", [])

    def get_isort_required_imports(self) -> list[str]:
        """Get required imports for isort."""
        isort_config = self.get_isort_config()
        return isort_config.get("required-imports", [])

    def is_isort_force_single_line(self) -> bool:
        """Check if isort should force single line imports."""
        isort_config = self.get_isort_config()
        return isort_config.get("force-single-line", False)

    def is_isort_combine_as_imports(self) -> bool:
        """Check if isort should combine as imports."""
        isort_config = self.get_isort_config()
        return isort_config.get("combine-as-imports", False)

    def get_isort_section_order(self) -> list[str]:
        """Get the section order for isort."""
        isort_config = self.get_isort_config()
        return isort_config.get("section-order", [
            "future", "standard-library", "third-party",
            "first-party", "local-folder"
        ])

    def get_flake8_annotations_config(self) -> dict[str, Any]:
        """Get flake8-annotations configuration."""
        lint_config = self.get_lint_config()
        return lint_config.get("flake8-annotations", {})

    def get_flake8_bandit_config(self) -> dict[str, Any]:
        """Get flake8-bandit configuration."""
        lint_config = self.get_lint_config()
        return lint_config.get("flake8-bandit", {})

    def get_flake8_bugbear_config(self) -> dict[str, Any]:
        """Get flake8-bugbear configuration."""
        lint_config = self.get_lint_config()
        return lint_config.get("flake8-bugbear", {})

    def get_flake8_builtins_config(self) -> dict[str, Any]:
        """Get flake8-builtins configuration."""
        lint_config = self.get_lint_config()
        return lint_config.get("flake8-builtins", {})

    def get_flake8_comprehensions_config(self) -> dict[str, Any]:
        """Get flake8-comprehensions configuration."""
        lint_config = self.get_lint_config()
        return lint_config.get("flake8-comprehensions", {})

    def get_flake8_errmsg_config(self) -> dict[str, Any]:
        """Get flake8-errmsg configuration."""
        lint_config = self.get_lint_config()
        return lint_config.get("flake8-errmsg", {})

    def get_flake8_import_conventions_config(self) -> dict[str, Any]:
        """Get flake8-import-conventions configuration."""
        lint_config = self.get_lint_config()
        return lint_config.get("flake8-import-conventions", {})

    def get_flake8_pytest_style_config(self) -> dict[str, Any]:
        """Get flake8-pytest-style configuration."""
        lint_config = self.get_lint_config()
        return lint_config.get("flake8-pytest-style", {})

    def get_flake8_quotes_config(self) -> dict[str, Any]:
        """Get flake8-quotes configuration."""
        lint_config = self.get_lint_config()
        return lint_config.get("flake8-quotes", {})

    def get_flake8_self_config(self) -> dict[str, Any]:
        """Get flake8-self configuration."""
        lint_config = self.get_lint_config()
        return lint_config.get("flake8-self", {})

    def get_flake8_tidy_imports_config(self) -> dict[str, Any]:
        """Get flake8-tidy-imports configuration."""
        lint_config = self.get_lint_config()
        return lint_config.get("flake8-tidy-imports", {})

    def get_flake8_type_checking_config(self) -> dict[str, Any]:
        """Get flake8-type-checking configuration."""
        lint_config = self.get_lint_config()
        return lint_config.get("flake8-type-checking", {})

    def get_flake8_unused_arguments_config(self) -> dict[str, Any]:
        """Get flake8-unused-arguments configuration."""
        lint_config = self.get_lint_config()
        return lint_config.get("flake8-unused-arguments", {})

    def get_mccabe_config(self) -> dict[str, Any]:
        """Get mccabe configuration."""
        lint_config = self.get_lint_config()
        return lint_config.get("mccabe", {})

    def get_mccabe_max_complexity(self) -> int:
        """Get the maximum complexity for mccabe."""
        mccabe_config = self.get_mccabe_config()
        return mccabe_config.get("max-complexity", 10)

    def get_pep8_naming_config(self) -> dict[str, Any]:
        """Get pep8-naming configuration."""
        lint_config = self.get_lint_config()
        return lint_config.get("pep8-naming", {})

    def get_pycodestyle_config(self) -> dict[str, Any]:
        """Get pycodestyle configuration."""
        lint_config = self.get_lint_config()
        return lint_config.get("pycodestyle", {})

    def get_pycodestyle_max_line_length(self) -> int:
        """Get max line length for pycodestyle (E501)."""
        pycodestyle_config = self.get_pycodestyle_config()
        return pycodestyle_config.get("max-line-length", self.get_line_length())

    def get_pycodestyle_max_doc_length(self) -> int | None:
        """Get max doc line length for pycodestyle (W505)."""
        pycodestyle_config = self.get_pycodestyle_config()
        return pycodestyle_config.get("max-doc-length")

    def get_pydoclint_config(self) -> dict[str, Any]:
        """Get pydoclint configuration."""
        lint_config = self.get_lint_config()
        return lint_config.get("pydoclint", {})

    def get_pydocstyle_config(self) -> dict[str, Any]:
        """Get pydocstyle configuration."""
        lint_config = self.get_lint_config()
        return lint_config.get("pydocstyle", {})

    def get_pydocstyle_convention(self) -> str | None:
        """Get the docstring convention (google, numpy, pep257)."""
        pydocstyle_config = self.get_pydocstyle_config()
        return pydocstyle_config.get("convention")

    def get_pyflakes_config(self) -> dict[str, Any]:
        """Get pyflakes configuration."""
        lint_config = self.get_lint_config()
        return lint_config.get("pyflakes", {})

    def get_pylint_config(self) -> dict[str, Any]:
        """Get pylint configuration."""
        lint_config = self.get_lint_config()
        return lint_config.get("pylint", {})

    def get_pylint_max_args(self) -> int:
        """Get max arguments for pylint (PLR0913)."""
        pylint_config = self.get_pylint_config()
        return pylint_config.get("max-args", 5)

    def get_pylint_max_branches(self) -> int:
        """Get max branches for pylint (PLR0912)."""
        pylint_config = self.get_pylint_config()
        return pylint_config.get("max-branches", 12)

    def get_pylint_max_returns(self) -> int:
        """Get max returns for pylint (PLR0911)."""
        pylint_config = self.get_pylint_config()
        return pylint_config.get("max-returns", 6)

    def get_pylint_max_statements(self) -> int:
        """Get max statements for pylint (PLR0915)."""
        pylint_config = self.get_pylint_config()
        return pylint_config.get("max-statements", 50)

    def get_pyupgrade_config(self) -> dict[str, Any]:
        """Get pyupgrade configuration."""
        lint_config = self.get_lint_config()
        return lint_config.get("pyupgrade", {})

    def get_ruff_config(self) -> dict[str, Any]:
        """Get ruff-specific configuration."""
        lint_config = self.get_lint_config()
        return lint_config.get("ruff", {})

    # ========== Helper Methods ==========

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

        # Check if rule prefix is ignored
        for ignore in ignored:
            if rule.startswith(ignore):
                return False

        # Check if rule or its prefix is selected
        for sel in selected:
            if sel == "ALL" or rule == sel or rule.startswith(sel):
                return True

        return False

    def is_rule_fixable(self, rule: str) -> bool:
        """Check if a rule is fixable.

        Args:
            rule: Rule code (e.g., 'E501', 'F401').

        Returns:
            True if the rule can be auto-fixed.
        """
        fixable = self.get_fixable_rules()
        unfixable = self.get_unfixable_rules()

        # Check if explicitly unfixable
        if rule in unfixable:
            return False

        for unfix in unfixable:
            if rule.startswith(unfix):
                return False

        # Check if rule or its prefix is fixable
        for fix in fixable:
            if fix == "ALL" or rule == fix or rule.startswith(fix):
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

            # Find matching prefix (longest match first)
            best_match = None
            for prefix in RULE_PREFIX_MAPPING:
                if rule == prefix or rule.startswith(prefix):
                    if best_match is None or len(prefix) > len(best_match):
                        best_match = prefix

            if best_match:
                tools.add(RULE_PREFIX_MAPPING[best_match])

        return tools

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
            parts = pattern.split("**")
            if len(parts) == 2:
                prefix, suffix = parts
                if suffix:
                    suffix = suffix.lstrip("/")
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
            mode: Optional mode ('lint' or 'format') for section-specific excludes.

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

    # ========== Deprecated/Legacy Methods ==========

    def get_flake8_annotations_suppress_none_returning(self) -> bool:
        """Get suppress-none-returning option for flake8-annotations."""
        ann_config = self.get_flake8_annotations_config()
        return ann_config.get("suppress-none-returning", False)

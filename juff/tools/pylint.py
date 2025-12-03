"""Pylint tool wrapper."""

import re
from pathlib import Path

from juff.tools.base import BaseTool


class PylintTool(BaseTool):
    """Wrapper for pylint linter (PL rules)."""

    name = "pylint"

    def build_args(
        self,
        paths: list[Path],
        fix: bool = False,
        extra_args: list[str] | None = None,
    ) -> list[str]:
        """Build pylint command-line arguments.

        Args:
            paths: Paths to check.
            fix: Not applicable for pylint (it doesn't auto-fix).
            extra_args: Additional arguments.

        Returns:
            List of command-line arguments.
        """
        args = [
            "--output-format=text",
            "--msg-template={path}:{line}:{column}: {msg_id} {msg}",
        ]

        if self.config:
            # Get selected rules and filter to pylint-only
            selected = self.config.get_selected_rules()
            ignored = self.config.get_ignored_rules()

            # Filter to PL* rules (pylint rules)
            pylint_enable = []
            for rule in selected:
                if rule.startswith(("PL", "C", "R", "W", "E")) and self._is_pylint_rule(
                    rule
                ):
                    pylint_enable.append(self._convert_to_pylint_code(rule))

            pylint_disable = []
            for rule in ignored:
                if self._is_pylint_rule(rule):
                    pylint_disable.append(self._convert_to_pylint_code(rule))

            if pylint_enable:
                args.extend(["--enable", ",".join(pylint_enable)])

            if pylint_disable:
                args.extend(["--disable", ",".join(pylint_disable)])

            # Exclude patterns
            excludes = self.config.get_exclude_patterns(mode=self.mode)
            if excludes:
                for pattern in excludes:
                    args.extend(["--ignore-patterns", pattern])

        if extra_args:
            args.extend(extra_args)

        args.extend(str(p) for p in paths)

        return args

    def _is_pylint_rule(self, rule: str) -> bool:
        """Check if a rule is a pylint rule.

        Args:
            rule: Rule code.

        Returns:
            True if this is a pylint rule (PLC, PLE, PLR, PLW).
        """
        return rule.startswith(("PLC", "PLE", "PLR", "PLW"))

    def _convert_to_pylint_code(self, rule: str) -> str:
        """Convert ruff-style PL code to pylint code.

        Args:
            rule: Ruff-style rule code (e.g., PLC0414).

        Returns:
            Pylint-style code (e.g., C0414).
        """
        # PLC0414 -> C0414, PLE0001 -> E0001, etc.
        if rule.startswith("PLC"):
            return "C" + rule[3:]
        elif rule.startswith("PLE"):
            return "E" + rule[3:]
        elif rule.startswith("PLR"):
            return "R" + rule[3:]
        elif rule.startswith("PLW"):
            return "W" + rule[3:]
        return rule

    def parse_output(self, stdout: str, stderr: str) -> tuple[int, int]:
        """Parse pylint output.

        Args:
            stdout: Standard output from pylint.
            stderr: Standard error from pylint.

        Returns:
            Tuple of (issues_found, issues_fixed).
        """
        # Count lines matching pylint output format
        # Format: path:line:col: CODE message
        pattern = r"^.+:\d+:\d+: [CRWEF]\d+"
        issues = len(re.findall(pattern, stdout, re.MULTILINE))
        return issues, 0  # pylint doesn't auto-fix

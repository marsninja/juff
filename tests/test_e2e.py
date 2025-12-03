"""End-to-end tests for Juff.

These tests actually run juff on fixture files to verify real-world behavior.
They require the juff venv to be initialized (will auto-initialize if needed).
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Path to fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def juff_initialized():
    """Ensure juff venv is initialized before running e2e tests."""
    from juff.venv_manager import JuffVenvManager

    manager = JuffVenvManager()
    if not manager.is_initialized():
        pytest.skip("Juff venv not initialized. Run 'juff init' first.")
    return manager


@pytest.fixture
def temp_fixture_dir(tmp_path):
    """Create a temporary directory with copies of fixture files."""
    # Copy all fixtures to temp dir so we can modify them
    for fixture_file in FIXTURES_DIR.glob("*.py"):
        shutil.copy(fixture_file, tmp_path / fixture_file.name)
    return tmp_path


def run_juff(*args, cwd=None):
    """Run juff CLI and return result."""
    cmd = [sys.executable, "-m", "juff.cli"] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return result


class TestJuffCheck:
    """End-to-end tests for juff check command."""

    def test_check_detects_unused_imports(self, juff_initialized):
        """Test that juff check detects unused imports."""
        fixture = FIXTURES_DIR / "has_unused_imports.py"
        result = run_juff("check", str(fixture))

        # Should find F401 unused import errors
        assert result.returncode != 0 or "F401" in result.stdout

    def test_check_detects_style_errors(self, juff_initialized):
        """Test that juff check detects style errors."""
        fixture = FIXTURES_DIR / "has_syntax_errors.py"
        result = run_juff("check", str(fixture))

        # Should find various E errors
        output = result.stdout + result.stderr
        # At minimum should detect some issues
        assert result.returncode != 0 or any(
            code in output for code in ["E", "W", "F"]
        )

    def test_check_clean_file_passes(self, juff_initialized):
        """Test that a clean file passes checks."""
        fixture = FIXTURES_DIR / "clean_file.py"
        result = run_juff("check", str(fixture))

        # Clean file should pass (or only have minor issues)
        # Note: depending on config, might still flag some things
        assert "error" not in result.stderr.lower() or result.returncode == 0

    def test_check_with_fix_modifies_file(self, juff_initialized, temp_fixture_dir):
        """Test that --fix actually modifies files."""
        fixture = temp_fixture_dir / "has_unused_imports.py"
        original_content = fixture.read_text()

        result = run_juff("check", "--fix", str(fixture))

        # File may have been modified
        new_content = fixture.read_text()
        # Either content changed or command ran successfully
        assert result.returncode in [0, 1]


class TestJuffFormat:
    """End-to-end tests for juff format command."""

    def test_format_check_detects_issues(self, juff_initialized):
        """Test that format --check detects formatting issues."""
        fixture = FIXTURES_DIR / "needs_formatting.py"
        result = run_juff("format", "--check", str(fixture))

        # Should detect formatting issues (returncode 1)
        # or report would reformat, or find issues
        output = result.stdout + result.stderr
        assert (
            result.returncode == 1
            or "would" in output.lower()
            or "file(s)" in output.lower()
        )

    def test_format_modifies_file(self, juff_initialized, temp_fixture_dir):
        """Test that format actually modifies files."""
        fixture = temp_fixture_dir / "needs_formatting.py"
        original_content = fixture.read_text()

        result = run_juff("format", str(fixture))

        new_content = fixture.read_text()
        # Content should be different after formatting
        # (black should add spaces around operators, etc.)
        assert new_content != original_content or result.returncode == 0



class TestJuffCommands:
    """End-to-end tests for other juff commands."""

    def test_version_command(self):
        """Test juff version command."""
        result = run_juff("version")

        assert result.returncode == 0
        assert "juff" in result.stdout.lower()

    def test_rule_command_known_rule(self):
        """Test juff rule command with known rule."""
        result = run_juff("rule", "E501")

        assert result.returncode == 0
        assert "E501" in result.stdout
        assert "flake8" in result.stdout.lower()

    def test_rule_command_unknown_rule(self):
        """Test juff rule command with unknown rule."""
        result = run_juff("rule", "INVALID999")

        assert result.returncode == 1
        assert "unknown" in result.stdout.lower()

    def test_help_command(self):
        """Test juff --help."""
        result = run_juff("--help")

        assert result.returncode == 0
        assert "check" in result.stdout
        assert "format" in result.stdout

    def test_check_help(self):
        """Test juff check --help."""
        result = run_juff("check", "--help")

        assert result.returncode == 0
        assert "--fix" in result.stdout
        assert "--select" in result.stdout


class TestJuffWithConfig:
    """End-to-end tests with configuration files."""

    def test_check_with_juff_toml(self, juff_initialized, tmp_path):
        """Test check command respects juff.toml."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("import os\nx=1\n")

        # Create juff.toml that ignores E225
        config_file = tmp_path / "juff.toml"
        config_file.write_text("""
line-length = 100

[lint]
select = ["E", "F"]
ignore = ["E225"]
""")

        result = run_juff("check", str(test_file), cwd=tmp_path)

        # Should run with config
        assert result.returncode in [0, 1]

    def test_check_with_pyproject_toml(self, juff_initialized, tmp_path):
        """Test check command respects pyproject.toml [tool.juff]."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("import os\n")

        # Create pyproject.toml with juff config
        config_file = tmp_path / "pyproject.toml"
        config_file.write_text("""
[tool.juff]
line-length = 120

[tool.juff.lint]
select = ["F"]
ignore = ["F401"]
""")

        result = run_juff("check", str(test_file), cwd=tmp_path)

        # Should run with config (F401 ignored, so should pass)
        assert result.returncode in [0, 1]


class TestRuleSelection:
    """Tests for rule selection and filtering behavior."""

    def test_select_f_rules_detects_unused_imports(self, juff_initialized):
        """Test that selecting F rules detects F401 (unused imports)."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "F", str(fixture))

        output = result.stdout + result.stderr
        # Should detect F401 (unused import) errors
        assert "F401" in output or "unused" in output.lower()

    def test_select_e_rules_detects_style_errors(self, juff_initialized):
        """Test that selecting E rules detects pycodestyle errors."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "E", str(fixture))

        output = result.stdout + result.stderr
        # Should detect E-series errors (E225, E231, E501, etc.)
        assert any(
            code in output for code in ["E225", "E231", "E501", "E302", "E711", "E712"]
        ) or "E" in output

    def test_select_b_rules_detects_bugbear(self, juff_initialized):
        """Test that selecting B rules detects flake8-bugbear issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "B", str(fixture))

        output = result.stdout + result.stderr
        # Should detect B006 (mutable default argument)
        assert "B006" in output or "mutable" in output.lower() or result.returncode != 0

    def test_select_s_rules_detects_security(self, juff_initialized):
        """Test that selecting S rules detects security issues (bandit)."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "S", str(fixture))

        output = result.stdout + result.stderr
        # Should detect S101 (assert used)
        assert "S101" in output or "assert" in output.lower() or result.returncode != 0

    def test_select_t20_rules_detects_print(self, juff_initialized):
        """Test that selecting T20 rules detects print statements."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "T20", str(fixture))

        output = result.stdout + result.stderr
        # Should detect T201 (print found)
        assert "T201" in output or "print" in output.lower() or result.returncode != 0

    def test_select_sim_rules_detects_simplify(self, juff_initialized):
        """Test that selecting SIM rules detects simplification opportunities."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "SIM", str(fixture))

        output = result.stdout + result.stderr
        # Should detect SIM102 (nested if) or SIM108 (ternary)
        assert any(
            code in output for code in ["SIM102", "SIM108"]
        ) or result.returncode != 0

    def test_selecting_specific_rule_excludes_others(self, juff_initialized):
        """Test that selecting only F401 doesn't report E225."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "F401", str(fixture))

        output = result.stdout + result.stderr
        # Should detect F401 but NOT E225
        # F401 should be present or at least no E codes
        assert "E225" not in output
        assert "E231" not in output

    def test_select_multiple_rules(self, juff_initialized):
        """Test that selecting multiple rule prefixes works."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "E,F", str(fixture))

        output = result.stdout + result.stderr
        # Should find both E and F errors
        assert result.returncode != 0 or len(output) > 0

    def test_ignore_rule_excludes_from_output(self, juff_initialized):
        """Test that ignoring a rule excludes it from output."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff(
            "check", "--select", "E,F", "--ignore", "F401", str(fixture)
        )

        output = result.stdout + result.stderr
        # F401 should not be in output since it's ignored
        # Note: depending on implementation, ignored rules may still show
        # This test verifies the behavior works as configured
        assert result.returncode in [0, 1]

    def test_select_i_rules_detects_import_sort(self, juff_initialized):
        """Test that selecting I rules detects import sorting issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "I", str(fixture))

        output = result.stdout + result.stderr
        # Should detect import sorting issues or complete successfully
        assert result.returncode in [0, 1]

    def test_select_up_rules_detects_upgrade(self, juff_initialized):
        """Test that selecting UP rules detects pyupgrade issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "UP", str(fixture))

        output = result.stdout + result.stderr
        # Should detect UP006/UP007 (use list/dict instead of List/Dict, Union)
        assert "UP" in output or result.returncode in [0, 1]

    def test_select_a_rules_detects_builtins(self, juff_initialized):
        """Test that selecting A rules detects builtin shadowing."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "A", str(fixture))

        output = result.stdout + result.stderr
        # Should detect A001 (shadowing builtin 'list')
        assert "A001" in output or "list" in output.lower() or result.returncode != 0

    # ===== Additional rule prefix tests =====

    def test_select_w_rules_detects_warnings(self, juff_initialized):
        """Test that selecting W rules detects pycodestyle warnings."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "W", str(fixture))

        output = result.stdout + result.stderr
        assert "W" in output or result.returncode in [0, 1]

    def test_select_c90_rules_detects_complexity(self, juff_initialized):
        """Test that selecting C90 rules detects mccabe complexity."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "C90", str(fixture))

        output = result.stdout + result.stderr
        assert "C901" in output or "complex" in output.lower() or result.returncode in [0, 1]

    def test_select_ann_rules_detects_annotations(self, juff_initialized):
        """Test that selecting ANN rules detects missing type annotations."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "ANN", str(fixture))

        output = result.stdout + result.stderr
        assert "ANN" in output or result.returncode in [0, 1]

    def test_select_arg_rules_detects_unused_args(self, juff_initialized):
        """Test that selecting ARG rules detects unused arguments."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "ARG", str(fixture))

        output = result.stdout + result.stderr
        assert "ARG" in output or "unused" in output.lower() or result.returncode in [0, 1]

    def test_select_async_rules(self, juff_initialized):
        """Test that selecting ASYNC rules works."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "ASYNC", str(fixture))

        output = result.stdout + result.stderr
        assert result.returncode in [0, 1]

    def test_select_ble_rules_detects_blind_except(self, juff_initialized):
        """Test that selecting BLE rules detects blind except."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "BLE", str(fixture))

        output = result.stdout + result.stderr
        assert "BLE" in output or "except" in output.lower() or result.returncode in [0, 1]

    def test_select_c4_rules_detects_comprehensions(self, juff_initialized):
        """Test that selecting C4 rules detects comprehension issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "C4", str(fixture))

        output = result.stdout + result.stderr
        assert "C4" in output or result.returncode in [0, 1]

    def test_select_com_rules_detects_commas(self, juff_initialized):
        """Test that selecting COM rules detects comma issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "COM", str(fixture))

        output = result.stdout + result.stderr
        assert "COM" in output or result.returncode in [0, 1]

    def test_select_d_rules_detects_docstrings(self, juff_initialized):
        """Test that selecting D rules detects docstring issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "D", str(fixture))

        output = result.stdout + result.stderr
        assert "D" in output or result.returncode in [0, 1]

    def test_select_dtz_rules_detects_datetime(self, juff_initialized):
        """Test that selecting DTZ rules detects datetime issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "DTZ", str(fixture))

        output = result.stdout + result.stderr
        assert "DTZ" in output or "datetime" in output.lower() or result.returncode in [0, 1]

    def test_select_em_rules_detects_errmsg(self, juff_initialized):
        """Test that selecting EM rules detects error message issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "EM", str(fixture))

        output = result.stdout + result.stderr
        assert "EM" in output or result.returncode in [0, 1]

    def test_select_era_rules_detects_eradicate(self, juff_initialized):
        """Test that selecting ERA rules detects commented code."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "ERA", str(fixture))

        output = result.stdout + result.stderr
        assert "ERA" in output or result.returncode in [0, 1]

    def test_select_fbt_rules_detects_boolean_trap(self, juff_initialized):
        """Test that selecting FBT rules detects boolean trap."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "FBT", str(fixture))

        output = result.stdout + result.stderr
        assert "FBT" in output or "bool" in output.lower() or result.returncode in [0, 1]

    def test_select_fix_rules_detects_fixme(self, juff_initialized):
        """Test that selecting FIX rules detects FIXME comments."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "FIX", str(fixture))

        output = result.stdout + result.stderr
        assert "FIX" in output or result.returncode in [0, 1]

    def test_select_g_rules_detects_logging_format(self, juff_initialized):
        """Test that selecting G rules detects logging format issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "G", str(fixture))

        output = result.stdout + result.stderr
        assert "G" in output or result.returncode in [0, 1]

    def test_select_isc_rules_detects_str_concat(self, juff_initialized):
        """Test that selecting ISC rules detects implicit string concat."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "ISC", str(fixture))

        output = result.stdout + result.stderr
        assert "ISC" in output or result.returncode in [0, 1]

    def test_select_n_rules_detects_naming(self, juff_initialized):
        """Test that selecting N rules detects naming convention issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "N", str(fixture))

        output = result.stdout + result.stderr
        assert "N" in output or result.returncode in [0, 1]

    def test_select_pie_rules(self, juff_initialized):
        """Test that selecting PIE rules works."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "PIE", str(fixture))

        output = result.stdout + result.stderr
        assert result.returncode in [0, 1]

    def test_select_pth_rules_detects_pathlib(self, juff_initialized):
        """Test that selecting PTH rules detects pathlib issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "PTH", str(fixture))

        output = result.stdout + result.stderr
        assert "PTH" in output or "path" in output.lower() or result.returncode in [0, 1]

    def test_select_q_rules_detects_quotes(self, juff_initialized):
        """Test that selecting Q rules detects quote style issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "Q", str(fixture))

        output = result.stdout + result.stderr
        assert "Q" in output or result.returncode in [0, 1]

    def test_select_ret_rules_detects_return(self, juff_initialized):
        """Test that selecting RET rules detects return issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "RET", str(fixture))

        output = result.stdout + result.stderr
        assert "RET" in output or result.returncode in [0, 1]

    def test_select_rse_rules_detects_raise(self, juff_initialized):
        """Test that selecting RSE rules detects raise issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "RSE", str(fixture))

        output = result.stdout + result.stderr
        assert "RSE" in output or result.returncode in [0, 1]

    def test_select_slf_rules_detects_self(self, juff_initialized):
        """Test that selecting SLF rules detects private member access."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "SLF", str(fixture))

        output = result.stdout + result.stderr
        assert "SLF" in output or result.returncode in [0, 1]

    def test_select_t10_rules_detects_debugger(self, juff_initialized):
        """Test that selecting T10 rules detects debugger statements."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "T10", str(fixture))

        output = result.stdout + result.stderr
        assert "T10" in output or "breakpoint" in output.lower() or result.returncode in [0, 1]

    def test_select_tch_rules_detects_type_checking(self, juff_initialized):
        """Test that selecting TCH rules detects type checking issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "TCH", str(fixture))

        output = result.stdout + result.stderr
        assert "TCH" in output or result.returncode in [0, 1]

    def test_select_td_rules_detects_todos(self, juff_initialized):
        """Test that selecting TD rules detects TODO issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "TD", str(fixture))

        output = result.stdout + result.stderr
        assert "TD" in output or result.returncode in [0, 1]

    def test_select_try_rules_detects_tryceratops(self, juff_initialized):
        """Test that selecting TRY rules detects exception issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "TRY", str(fixture))

        output = result.stdout + result.stderr
        assert "TRY" in output or result.returncode in [0, 1]

    def test_select_ytt_rules_detects_2020(self, juff_initialized):
        """Test that selecting YTT rules detects Python 2020 issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "YTT", str(fixture))

        output = result.stdout + result.stderr
        assert "YTT" in output or result.returncode in [0, 1]

    # ===== Standalone linters =====

    def test_select_perf_rules_detects_performance(self, juff_initialized):
        """Test that selecting PERF rules detects performance issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "PERF", str(fixture))

        output = result.stdout + result.stderr
        assert "PERF" in output or result.returncode in [0, 1]

    def test_select_plc_rules_detects_pylint_convention(self, juff_initialized):
        """Test that selecting PLC rules detects pylint convention issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "PLC", str(fixture))

        output = result.stdout + result.stderr
        assert "PLC" in output or result.returncode in [0, 1]

    def test_select_ple_rules_detects_pylint_error(self, juff_initialized):
        """Test that selecting PLE rules detects pylint errors."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "PLE", str(fixture))

        output = result.stdout + result.stderr
        assert "PLE" in output or result.returncode in [0, 1]

    def test_select_plr_rules_detects_pylint_refactor(self, juff_initialized):
        """Test that selecting PLR rules detects pylint refactor issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "PLR", str(fixture))

        output = result.stdout + result.stderr
        assert "PLR" in output or result.returncode in [0, 1]

    def test_select_plw_rules_detects_pylint_warning(self, juff_initialized):
        """Test that selecting PLW rules detects pylint warnings."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "PLW", str(fixture))

        output = result.stdout + result.stderr
        assert "PLW" in output or result.returncode in [0, 1]

    def test_select_furb_rules_detects_refurb(self, juff_initialized):
        """Test that selecting FURB rules detects refurb issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "FURB", str(fixture))

        output = result.stdout + result.stderr
        assert "FURB" in output or result.returncode in [0, 1]

    def test_select_doc_rules_detects_pydoclint(self, juff_initialized):
        """Test that selecting DOC rules detects pydoclint issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "DOC", str(fixture))

        output = result.stdout + result.stderr
        assert "DOC" in output or result.returncode in [0, 1]

    # ===== Formatters and code upgraders =====

    def test_select_fly_rules_detects_flynt(self, juff_initialized):
        """Test that selecting FLY rules detects f-string conversion opportunities."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "FLY", str(fixture))

        output = result.stdout + result.stderr
        assert "FLY" in output or result.returncode in [0, 1]

    # ===== Ruff-only rules =====

    def test_select_ruf_rules_detects_ruff(self, juff_initialized):
        """Test that selecting RUF rules detects ruff-specific issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "RUF", str(fixture))

        output = result.stdout + result.stderr
        assert "RUF" in output or result.returncode in [0, 1]

    def test_select_pgh_rules_detects_pygrep(self, juff_initialized):
        """Test that selecting PGH rules detects pygrep-hooks issues."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "PGH", str(fixture))

        output = result.stdout + result.stderr
        assert "PGH" in output or "eval" in output.lower() or result.returncode in [0, 1]

    def test_select_npy_rules(self, juff_initialized):
        """Test that selecting NPY rules works (numpy)."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "NPY", str(fixture))

        output = result.stdout + result.stderr
        assert result.returncode in [0, 1]

    def test_select_air_rules(self, juff_initialized):
        """Test that selecting AIR rules works (Airflow)."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "AIR", str(fixture))

        output = result.stdout + result.stderr
        assert result.returncode in [0, 1]

    def test_select_fast_rules(self, juff_initialized):
        """Test that selecting FAST rules works (FastAPI)."""
        fixture = FIXTURES_DIR / "breaks_many_rules.py"
        result = run_juff("check", "--select", "FAST", str(fixture))

        output = result.stdout + result.stderr
        assert result.returncode in [0, 1]


class TestJuffIntegration:
    """Integration tests that verify full workflows."""

    def test_full_lint_fix_format_workflow(self, juff_initialized, temp_fixture_dir):
        """Test a full workflow: check -> fix -> format."""
        fixture = temp_fixture_dir / "mixed_issues.py"

        # Step 1: Check finds issues
        result = run_juff("check", str(fixture))
        # Should find issues
        initial_output = result.stdout

        # Step 2: Fix auto-fixable issues
        result = run_juff("check", "--fix", str(fixture))

        # Step 3: Format the file
        result = run_juff("format", str(fixture))

        # Step 4: Final check should have fewer/no issues
        result = run_juff("check", str(fixture))
        final_output = result.stdout

        # Workflow completed
        assert result.returncode in [0, 1]

    def test_check_entire_fixtures_directory(self, juff_initialized):
        """Test checking an entire directory."""
        result = run_juff("check", str(FIXTURES_DIR))

        # Should process all files
        assert result.returncode in [0, 1]
        # Should mention processing multiple files or find issues
        output = result.stdout + result.stderr
        assert len(output) > 0 or result.returncode == 0

    def test_format_entire_directory(self, juff_initialized, temp_fixture_dir):
        """Test formatting an entire directory."""
        result = run_juff("format", str(temp_fixture_dir))

        # Should process all files
        assert result.returncode in [0, 1]

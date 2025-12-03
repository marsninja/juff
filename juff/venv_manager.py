"""Virtual environment manager for Juff.

This module handles creation and management of the dedicated Juff virtual environment
in the user's home directory. It uses Python's stdlib venv module (with ensurepip) to
create the environment and subprocess to run pip (the recommended approach by pip
maintainers).
"""

import subprocess
import sys
import venv
from pathlib import Path
from typing import Optional


class JuffVenvManager:
    """Manages the Juff virtual environment and package installations."""

    # Default packages that replicate ruff's functionality
    DEFAULT_PACKAGES = [
        # Linting (flake8 + plugins for various rule sets)
        "flake8>=7.0.0",
        "flake8-bugbear>=24.0.0",  # B rules
        "flake8-comprehensions>=3.14.0",  # C4 rules
        "flake8-simplify>=0.21.0",  # SIM rules
        "flake8-pie>=0.16.0",  # PIE rules
        "flake8-bandit>=4.1.0",  # S rules (security)
        "flake8-builtins>=2.2.0",  # A rules
        "flake8-commas>=2.1.0",  # COM rules
        "flake8-debugger>=4.1.0",  # T10 rules
        "flake8-docstrings>=1.7.0",  # D rules
        "flake8-eradicate>=1.5.0",  # ERA rules
        "flake8-executable>=2.1.0",  # EXE rules
        "flake8-implicit-str-concat>=0.4.0",  # ISC rules
        "flake8-logging-format>=0.9.0",  # G rules
        "flake8-no-pep420>=2.7.0",  # INP rules
        "flake8-print>=5.0.0",  # T20 rules
        "flake8-pytest-style>=1.7.0",  # PT rules
        "flake8-quotes>=3.3.0",  # Q rules
        "flake8-return>=1.2.0",  # RET rules
        "flake8-self>=0.2.0",  # SLF rules
        "flake8-tidy-imports>=4.10.0",  # TID rules
        "flake8-type-checking>=2.9.0",  # TCH rules
        "flake8-use-pathlib>=0.3.0",  # PTH rules
        "pep8-naming>=0.13.0",  # N rules
        "flake8-annotations>=3.0.0",  # ANN rules
        "flake8-async>=22.11.0",  # ASYNC rules
        "flake8-blind-except>=0.2.0",  # BLE rules
        "flake8-boolean-trap>=1.0.0",  # FBT rules (if available)
        "flake8-raise>=0.0.5",  # RSE rules
        # "flake8-slots>=0.7.0",  # SLOT rules - disabled due to flake8 7.x incompatibility
        "flake8-gettext>=0.0.1",  # INT rules
        "tryceratops>=2.3.0",  # TRY rules
        "flake8-unused-arguments>=0.0.13",  # ARG rules
        "flake8-datetimez>=20.10.0",  # DTZ rules
        "flake8-errmsg>=0.4.0",  # EM rules
        "flake8-future-annotations>=1.1.0",  # FA rules
        # Formatting
        "black>=24.0.0",
        # Import sorting
        "isort>=5.13.0",
        # Code upgrades
        "pyupgrade>=3.15.0",
        # Additional utilities
        "autoflake>=2.2.0",  # F841, F401 autofixes
        "autopep8>=2.0.0",  # E/W autofixes
        # Extra fix tools
        "flynt>=1.0.0",  # Convert to f-strings (UP031, UP032)
        "docformatter>=1.7.0",  # Format docstrings (D rules)
        "add-trailing-comma>=3.1.0",  # Add trailing commas (COM812)
    ]

    def __init__(self, venv_path: Optional[Path] = None):
        """Initialize the venv manager.

        Args:
            venv_path: Optional custom path for the venv. Defaults to ~/.juff/venv
        """
        if venv_path is None:
            self.venv_path = Path.home() / ".juff" / "venv"
        else:
            self.venv_path = Path(venv_path)

        self.juff_home = self.venv_path.parent
        self._python_executable: Optional[Path] = None

    @property
    def python_executable(self) -> Path:
        """Get the path to the Python executable in the venv."""
        if self._python_executable is None:
            if sys.platform == "win32":
                self._python_executable = self.venv_path / "Scripts" / "python.exe"
            else:
                self._python_executable = self.venv_path / "bin" / "python"
        return self._python_executable

    @property
    def bin_path(self) -> Path:
        """Get the path to the bin/Scripts directory in the venv."""
        if sys.platform == "win32":
            return self.venv_path / "Scripts"
        return self.venv_path / "bin"

    def is_initialized(self) -> bool:
        """Check if the Juff venv is already initialized."""
        marker_file = self.juff_home / ".initialized"
        return marker_file.exists() and self.python_executable.exists()

    def ensure_initialized(self, force: bool = False) -> None:
        """Ensure the Juff venv is initialized with all required packages.

        Args:
            force: If True, recreate the venv even if it exists.
        """
        if self.is_initialized() and not force:
            return

        self._create_venv()
        self._install_packages(self.DEFAULT_PACKAGES)
        self._mark_initialized()

    def _create_venv(self) -> None:
        """Create the virtual environment."""
        # Ensure parent directory exists
        self.juff_home.mkdir(parents=True, exist_ok=True)

        # Remove existing venv if present
        if self.venv_path.exists():
            import shutil

            shutil.rmtree(self.venv_path)

        # Create new venv with pip
        builder = venv.EnvBuilder(
            system_site_packages=False,
            clear=True,
            with_pip=True,
            upgrade_deps=True,
        )
        builder.create(self.venv_path)

    def _run_pip(self, args: list[str], check: bool = False) -> subprocess.CompletedProcess:
        """Run pip in the venv using subprocess (recommended by pip maintainers).

        Args:
            args: Arguments to pass to pip.
            check: Whether to raise on non-zero exit code.

        Returns:
            CompletedProcess with the result.
        """
        return subprocess.run(
            [str(self.python_executable), "-m", "pip"] + args,
            capture_output=True,
            text=True,
            check=check,
        )

    def _install_packages(self, packages: list[str]) -> None:
        """Install packages into the venv using pip.

        Args:
            packages: List of package specifications to install.

        Raises:
            RuntimeError: If pip installation fails.
        """
        # First upgrade pip itself
        result = self._run_pip(["install", "--upgrade", "pip"])
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to upgrade pip:\n{result.stderr or result.stdout}"
            )

        # Install all packages
        result = self._run_pip(["install", "--upgrade"] + packages)
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to install packages:\n{result.stderr or result.stdout}"
            )

    def _mark_initialized(self) -> None:
        """Mark the venv as initialized."""
        marker_file = self.juff_home / ".initialized"
        marker_file.write_text(f"version={__import__('juff').__version__}\n")

    def get_tool_path(self, tool_name: str) -> Path:
        """Get the path to a tool executable in the venv.

        Args:
            tool_name: Name of the tool (e.g., 'flake8', 'black').

        Returns:
            Path to the tool executable.
        """
        if sys.platform == "win32":
            return self.bin_path / f"{tool_name}.exe"
        return self.bin_path / tool_name

    def run_tool(
        self, tool_name: str, args: list[str], **subprocess_kwargs
    ) -> subprocess.CompletedProcess:
        """Run a tool from the venv.

        Args:
            tool_name: Name of the tool to run.
            args: Arguments to pass to the tool.
            **subprocess_kwargs: Additional arguments for subprocess.run.

        Returns:
            CompletedProcess instance with the result.
        """
        self.ensure_initialized()
        tool_path = self.get_tool_path(tool_name)

        if not tool_path.exists():
            raise FileNotFoundError(f"Tool '{tool_name}' not found at {tool_path}")

        return subprocess.run([str(tool_path)] + args, **subprocess_kwargs)

    def install_additional_packages(self, packages: list[str]) -> None:
        """Install additional packages into the venv.

        Args:
            packages: List of package specifications to install.
        """
        self.ensure_initialized()
        self._install_packages(packages)

    def list_installed_packages(self) -> str:
        """List all installed packages in the venv.

        Returns:
            Output from pip list.
        """
        self.ensure_initialized()
        result = self._run_pip(["list"])
        return result.stdout

    def update_all_packages(self) -> None:
        """Update all packages in the venv to their latest versions."""
        self.ensure_initialized()
        self._install_packages(self.DEFAULT_PACKAGES)

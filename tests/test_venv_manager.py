"""Tests for Juff venv manager."""

import pytest
import sys
from pathlib import Path

from juff.venv_manager import JuffVenvManager


class TestJuffVenvManager:
    """Tests for JuffVenvManager class."""

    def test_default_venv_path(self):
        """Test that default venv path is in home directory."""
        manager = JuffVenvManager()

        assert manager.venv_path == Path.home() / ".juff" / "venv"
        assert manager.juff_home == Path.home() / ".juff"

    def test_custom_venv_path(self, temp_dir):
        """Test custom venv path."""
        custom_path = temp_dir / "custom_venv"
        manager = JuffVenvManager(venv_path=custom_path)

        assert manager.venv_path == custom_path
        assert manager.juff_home == temp_dir

    def test_python_executable_path_unix(self, temp_dir):
        """Test Python executable path on Unix-like systems."""
        manager = JuffVenvManager(venv_path=temp_dir / "venv")

        if sys.platform != "win32":
            assert manager.python_executable == temp_dir / "venv" / "bin" / "python"
        else:
            assert manager.python_executable == temp_dir / "venv" / "Scripts" / "python.exe"

    def test_bin_path(self, temp_dir):
        """Test bin/Scripts path."""
        manager = JuffVenvManager(venv_path=temp_dir / "venv")

        if sys.platform != "win32":
            assert manager.bin_path == temp_dir / "venv" / "bin"
        else:
            assert manager.bin_path == temp_dir / "venv" / "Scripts"

    def test_get_tool_path(self, temp_dir):
        """Test getting tool executable path."""
        manager = JuffVenvManager(venv_path=temp_dir / "venv")

        tool_path = manager.get_tool_path("flake8")

        if sys.platform != "win32":
            assert tool_path == temp_dir / "venv" / "bin" / "flake8"
        else:
            assert tool_path == temp_dir / "venv" / "Scripts" / "flake8.exe"

    def test_is_initialized_false_when_not_exists(self, temp_dir):
        """Test is_initialized returns False when venv doesn't exist."""
        manager = JuffVenvManager(venv_path=temp_dir / "nonexistent_venv")

        assert manager.is_initialized() is False

    def test_is_initialized_false_without_marker(self, temp_dir):
        """Test is_initialized returns False without marker file."""
        venv_path = temp_dir / "venv"
        venv_path.mkdir()

        # Create fake python executable
        bin_path = venv_path / ("Scripts" if sys.platform == "win32" else "bin")
        bin_path.mkdir()
        python_name = "python.exe" if sys.platform == "win32" else "python"
        (bin_path / python_name).touch()

        manager = JuffVenvManager(venv_path=venv_path)

        # Missing .initialized marker
        assert manager.is_initialized() is False

    def test_is_initialized_true_with_marker_and_python(self, temp_dir):
        """Test is_initialized returns True with marker and python."""
        venv_path = temp_dir / "venv"
        juff_home = temp_dir
        venv_path.mkdir()

        # Create fake python executable
        bin_path = venv_path / ("Scripts" if sys.platform == "win32" else "bin")
        bin_path.mkdir()
        python_name = "python.exe" if sys.platform == "win32" else "python"
        (bin_path / python_name).touch()

        # Create marker file
        (juff_home / ".initialized").touch()

        manager = JuffVenvManager(venv_path=venv_path)

        assert manager.is_initialized() is True

    def test_default_packages_list(self):
        """Test that DEFAULT_PACKAGES contains expected tools."""
        packages = JuffVenvManager.DEFAULT_PACKAGES

        # Check core packages are present
        package_names = [p.split(">=")[0].split("[")[0] for p in packages]

        assert "flake8" in package_names
        assert "black" in package_names
        assert "isort" in package_names
        assert "pyupgrade" in package_names
        assert "autoflake" in package_names
        assert "flake8-bugbear" in package_names

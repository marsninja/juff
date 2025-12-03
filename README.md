# Juff

A faithful Python-first drop-in replacement for [ruff](https://github.com/astral-sh/ruff).

## Philosophy

Instead of reimplementing the wonderful Python linting and formatting tools, Juff uses the **original visionary creators' packages** directly:

- **flake8** + plugins for linting (pycodestyle, pyflakes, and 40+ plugins)
- **black** for code formatting
- **isort** for import sorting
- **pyupgrade** for Python syntax upgrades
- **autoflake** for automatic fixes

Juff manages these tools in a dedicated virtual environment (`~/.juff/venv`), providing a seamless experience while honoring the original tool authors.

## Installation

```bash
pip install juff
```

## Quick Start

```bash
# Initialize the Juff environment (downloads and installs all tools)
juff init

# Lint your code
juff check .

# Lint and fix auto-fixable issues
juff check --fix .

# Format your code
juff format .

# Check formatting without applying changes
juff format --check .
```

## Configuration

Juff uses `juff.toml` (or `.juff.toml`, or `[tool.juff]` in `pyproject.toml`) for configuration. The format is compatible with `ruff.toml`:

```toml
# juff.toml
line-length = 88
target-version = "py311"

[lint]
select = ["E", "F", "W", "B", "I", "UP"]
ignore = ["E501"]

[format]
quote-style = "double"
```

### Supported Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `line-length` | Maximum line length | 88 |
| `target-version` | Target Python version | py311 |
| `exclude` | Patterns to exclude | [] |
| `include` | Patterns to include | ["*.py"] |

#### Lint Options (`[lint]`)

| Option | Description | Default |
|--------|-------------|---------|
| `select` | Rules to enable | ["E", "F", "W"] |
| `ignore` | Rules to ignore | [] |
| `fixable` | Rules that can be auto-fixed | ["ALL"] |
| `unfixable` | Rules that should not be auto-fixed | [] |

## Rule Codes

Juff supports the same rule code prefixes as ruff, mapped to their original tools:

| Prefix | Tool | Description |
|--------|------|-------------|
| E, W | flake8 (pycodestyle) | Style errors and warnings |
| F | flake8 (pyflakes) | Logical errors |
| B | flake8-bugbear | Bug and design problems |
| C4 | flake8-comprehensions | Comprehension issues |
| I | isort | Import sorting |
| UP | pyupgrade | Python upgrade opportunities |
| S | flake8-bandit | Security issues |
| N | pep8-naming | Naming conventions |
| D | flake8-docstrings | Docstring issues |
| ... | ... | And many more! |

## Commands

### `juff check [paths]`

Run linting checks on Python files.

```bash
juff check .                    # Check current directory
juff check src/ tests/          # Check specific directories
juff check --fix .              # Fix auto-fixable issues
juff check --select E,F .       # Only check specific rules
juff check --ignore E501 .      # Ignore specific rules
```

### `juff format [paths]`

Format Python files using black and isort.

```bash
juff format .                   # Format current directory
juff format --check .           # Check without applying changes
juff format --diff .            # Show diff of changes
```

### `juff init`

Initialize the Juff virtual environment and install all tools.

```bash
juff init                       # Initialize environment
juff init --force               # Force re-initialization
```

### `juff update`

Update all tools to their latest versions.

```bash
juff update
```

### `juff clean`

Remove the Juff virtual environment.

```bash
juff clean
```

### `juff version`

Show version information.

```bash
juff version                    # Show juff and key tool versions
juff version --verbose          # Show all installed packages
```

### `juff rule <code>`

Show information about a specific rule.

```bash
juff rule E501                  # Info about line length rule
juff rule F401                  # Info about unused import rule
```

## How It Works

1. **First Run**: When you first run any juff command, it creates a virtual environment at `~/.juff/venv` and installs all required Python tools.

2. **Tool Execution**: Juff orchestrates the underlying tools (flake8, black, isort, etc.) and aggregates their output into a unified format.

3. **Configuration**: Your `juff.toml` settings are translated into appropriate arguments for each underlying tool.

4. **Updates**: Run `juff update` to update all tools to their latest versions without affecting your project's dependencies.

## Comparison with Ruff

| Feature | Juff | Ruff |
|---------|------|------|
| Speed | Standard Python speed | Very fast (Rust) |
| Tool fidelity | 100% (uses original tools) | Reimplemented |
| Plugin support | All flake8 plugins | Limited subset |
| Memory usage | Higher (multiple processes) | Lower |
| Offline use | Requires initial download | Self-contained |

**When to use Juff:**
- You need exact compatibility with flake8/black/isort behavior
- You use flake8 plugins not supported by ruff
- You want to support the original tool authors
- You prefer Python-native tooling

**When to use Ruff:**
- Speed is critical
- You're working with very large codebases
- You want a single, self-contained binary

## Development

```bash
# Clone the repository
git clone https://github.com/Jaseci-Labs/juff.git
cd juff

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run juff on itself
juff check juff/
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Credits

Juff is built on the shoulders of giants:

- [flake8](https://flake8.pycqa.org/) by Tarek Ziade and the PyCQA team
- [black](https://black.readthedocs.io/) by Lukasz Langa
- [isort](https://pycqa.github.io/isort/) by Timothy Crosley
- [pyupgrade](https://github.com/asottile/pyupgrade) by Anthony Sottile
- [autoflake](https://github.com/PyCQA/autoflake) by the PyCQA team

And the many authors of flake8 plugins that make Python linting comprehensive.

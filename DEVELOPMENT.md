# Development Guide - TDX Tool

This document explains how to set up and work with the TDX Tool development environment across different systems.

## Quick Start

### Option 1: Using Conda (Recommended)

```bash
# Make setup script executable
chmod +x scripts/setup.sh

# Run setup script (creates environment from environment.yml)
./scripts/setup.sh

# Activate environment
conda activate tdx-dev

# Install package in development mode
make install-dev

# Run tests to verify setup
make test
```

### Option 2: Using pip

```bash
# Create Python 3.11 virtual environment
python3.11 -m venv venv

# Activate environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Install package in editable mode
pip install -e ".[dev]"

# Run tests
pytest
```

### Option 3: Using pyenv (For Python version management)

```bash
# Install Python 3.11 via pyenv
pyenv install 3.11.15

# Set local Python version
pyenv local 3.11.15

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements-dev.txt
pip install -e ".[dev]"
```

## Available Make Commands

| Command | Purpose |
|---------|---------|
| `make help` | Show all available commands |
| `make env-create` | Create conda environment |
| `make env-update` | Update conda environment |
| `make env-remove` | Remove conda environment |
| `make install` | Install package (editable mode) |
| `make install-dev` | Install package + development tools |
| `make lint` | Check code style with ruff |
| `make format` | Format code with ruff |
| `make type-check` | Run mypy type checker |
| `make test` | Run pytest |
| `make test-verbose` | Run pytest with verbose output |
| `make clean` | Remove build artifacts and caches |

## Python Version

The project requires Python >= 3.10. The default is Python 3.11 (specified in `.python-version`).

**Supported versions:**
- Python 3.10
- Python 3.11 (recommended)
- Python 3.12

## Core Dependencies

| Package | Min Version | Purpose |
|---------|------------|---------|
| requests | 2.31 | HTTP library |
| pandas | 2.2 | Data manipulation |
| geopandas | 0.14 | Geospatial data |
| pyarrow | 15 | Data serialization |
| msgspec | 0.18 | Fast serialization |
| shapely | 2.0 | Geometric operations |
| pyproj | 3.6 | Coordinate transformations |

## Development Tools

| Tool | Purpose |
|------|---------|
| pytest | Testing framework |
| pytest-mock | Mocking support |
| ruff | Fast linter & formatter |
| mypy | Static type checking |
| jupyterlab | Interactive notebooks |

## Configuration Files

### environment.yml
Conda environment specification. Defines all dependencies and Python version.

```bash
conda env create -f environment.yml
```

### requirements.txt
Core production dependencies (pip format).

### requirements-dev.txt
Development dependencies. Includes requirements.txt and additional dev tools.

```bash
pip install -r requirements-dev.txt
```

### .python-version
Specifies Python 3.11. Used by pyenv and VS Code to select the correct interpreter.

### Makefile
Shortcuts for common development commands.

### pyproject.toml
Project metadata, dependencies, and tool configurations.

## Cross-System Notes

### macOS
- Recommended: Use conda or homebrew-installed Python
- Ensure Xcode Command Line Tools are installed: `xcode-select --install`

### Linux (Ubuntu/Debian)
```bash
# Install Python 3.11
sudo apt-get update
sudo apt-get install python3.11 python3.11-venv
```

### Windows
- Use WSL2 (Windows Subsystem for Linux) recommended
- Or use Miniconda/Anaconda for native Windows support
- Note: Some spatial libraries work best in Unix-like environments

### Docker
To containerize this environment:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements-dev.txt && pip install -e ".[dev]"
```

## Troubleshooting

### Conda environment not found
```bash
# Recreate environment
conda env create -f environment.yml --force-reinstall
```

### Permission denied when running scripts/setup.sh
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### Import errors for geospatial packages
These packages have system library dependencies. Using conda is recommended:
```bash
conda env create -f environment.yml
```

### mypy errors after upgrade
Clear cache and reinstall:
```bash
make clean
pip install --force-reinstall mypy
make type-check
```

## CI/CD Integration

The configuration is optimized for:
- **GitHub Actions**: Use `environment.yml` for Linux runners
- **Local development**: Use Makefile commands
- **Docker**: Use requirements.txt for container builds

## Project Structure

```
tdx_tool/
├── environment.yml        # Conda environment spec
├── requirements.txt       # Core dependencies
├── requirements-dev.txt   # Development dependencies
├── .python-version        # Python version (3.11)
├── scripts/
│   ├── setup.sh           # Automated setup script
│   └── create_conda_env.ps1 # Windows setup script
├── Makefile              # Development commands
├── pyproject.toml        # Project metadata
└── src/
    └── tdx_tool/         # Main package
```

## Next Steps

1. ✅ Choose your setup method above
2. ✅ Activate the environment
3. ✅ Run `make test` to verify setup
4. ✅ Check README.md for project usage
5. ✅ Start developing!

## Getting Help

For issues with:
- **Environment setup**: Check the Troubleshooting section
- **Code quality**: Run `make lint` and `make type-check`
- **Tests failing**: Run `make test-verbose` for detailed output

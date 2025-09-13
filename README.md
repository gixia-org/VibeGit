# VibeGit MCP Server

A Model Context Protocol (MCP) server for logging and analyzing AI assistant conversations.

## Prerequisites

You need only two steps to get started:

### Step 1: Installation

```bash
pip install vibegit-mcp
```

### Step 2: Configuration

Once installed, you can configure the MCP configuration file to enable the VibeGit MCP server. Assuming you are using VSCode, you can add a `mcp.json` file in the `.vscode/` directory of your project with the following content:

```json
{
  "servers": {
    "vibegit": {
      "type": "stdio",
      "command": "vibegit-mcp"
    }
  }
}
```

## Usage

After configuring the MCP server, you can start your AI Coding Agent in VSCode. The VibeGit MCP server will automatically log all conversation rounds to the `.vibe/` directory in your project root.

## Features

- Log complete conversation rounds between users and AI assistants
- Track file operations and tool usage

All the logs and data are stored in the `.vibe/` directory under the project root. The directory structure is as follows:

```
.vibe/
├── rounds/
│   ├── 2023-03/
│   │   ├── round-1.json
│   │   ├── round-2.json
│   ├── 2023-04/
│   │   ├── round-3.json
│   │   ├── round-4.json
├── index.jsonl
├── sessions/
│   ├── session-1.json
│   ├── session-2.json
```
Each `round-*.json` file contains detailed information about a single conversation round, including user inputs, AI responses, and any file operations and tool usage performed. The `index.jsonl` file provides a quick reference to all rounds, and the `sessions/` directory contains session metadata. Each session contains the consecutive rounds of conversations.

## Building and Publishing (For Maintainers)

This package uses modern Python packaging with `pyproject.toml`.

#### Prerequisites

Install build tools:
```bash
pip install build twine
```

Set up PyPI credentials in `~/.pypirc`:
```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = # your PyPI API token (pypi-...)

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = # your TestPyPI API token (pypi-...)
```

#### Release Process

1. **Update version** in `pyproject.toml`:
   ```toml
   version = "x.y.z"  # Increment as needed
   ```

2. **Clean previous builds**:
   ```bash
   rm -rf dist/ build/ *.egg-info
   ```

3. **Build the package**:
   ```bash
   python -m build
   ```

4. **Test upload to TestPyPI** (optional but recommended):
   ```bash
   python -m twine upload --repository testpypi dist/*
   ```

5. **Test installation from TestPyPI**:
   ```bash
   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ vibegit-mcp==x.y.z
   ```

6. **Upload to PyPI**:
   ```bash
   python -m twine upload dist/*
   ```

#### Notes

- Always test with TestPyPI first before publishing to PyPI
- Make sure to increment the version number for each release
- The package uses `pyproject.toml` for modern Python packaging standards
- Clean the `dist/` directory before building new releases

## License

MIT License
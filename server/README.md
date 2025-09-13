# VibeGit MCP Server

A Model Context Protocol (MCP) server for logging and analyzing AI assistant conversations.

## Installation

```bash
pip install vibegit-mcp
```

## Usage

Once installed, you can configure the MCP server in your client application by adding the following to your MCP configuration:

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

## Features

- Log complete conversation rounds between users and AI assistants
- Track file operations and tool usage
- Session management with automatic rotation
- Persistent storage of conversation history

## Environment Variables

- `VIBE_SESSION_TIMEOUT_MINUTES` (default: 30) - Session timeout in minutes

## Development

For local development:

```bash
cd server
pip install -e .
```

Run the server:

```bash
vibegit-mcp
```

Or:

```bash
python -m vibegit.server
```

## JSON-RPC Example

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"clientInfo":{"name":"manual","version":"0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"log_round","arguments":{
	"user_message":"请帮我写一个冒泡排序",
	"assistant_messages":["这是实现思路...","这是代码解释..."],
	"file_views":["src/sort.py"],
	"file_writes":["src/sort.py"],
	"tool_calls":[{"name":"explain_complexity","args_summary":"O(n^2) average"}],
	"status":"ok"
}}}
```

## Output

Generates files in `.vibe/rounds/<YYYY-MM>/round-*.json`, `index.jsonl`, and `sessions/`.

## Publishing (For Maintainers)

This package is published to PyPI for easy installation. Here's how to publish new versions:

### Prerequisites

1. Install publishing tools:
   ```bash
   pip install build twine
   ```

2. Set up PyPI credentials in `~/.pypirc`:
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

### Build and Publish

1. **Update version** in `setup.py`:
   ```python
   version="0.1.2",  # Increment as needed
   ```

2. **Build the package**:
   ```bash
   python setup.py sdist bdist_wheel
   ```

3. **Test upload to TestPyPI** (optional):
   ```bash
   twine upload --repository testpypi dist/* --verbose
   ```

4. **Test installation from TestPyPI**:
   ```bash
   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ vibegit-mcp==0.1.2
   ```

5. **Upload to PyPI**:
   ```bash
   twine upload dist/* --verbose
   ```

### Notes

- Always test with TestPyPI first before publishing to the main PyPI
- Make sure to increment the version number for each release
- The package uses `setup.py` for maximum compatibility with different setuptools versions
- Clean the `dist/` directory before building new releases: `rm -rf dist/`

## License

MIT License

# ffdecmcp

MCP (Model Context Protocol) wrapper for **JPEXS Free Flash Decompiler (FFDec)** - expose SWF decompilation and analysis tools to AI assistants like Claude.

## Tools

### 1. `decompile_swf`
Decompile all ActionScript code from a SWF file to organized directory structure.

**Parameters:**
- `swf_path` (required): Absolute path to SWF file
- `output_dir` (required): Directory for decompiled scripts
- `timeout` (optional): Timeout in seconds (default: 60)

### 2. `extract_actionscript`
Extract specific ActionScript classes by name (AS3 only). Faster than full decompilation when you only need specific classes.

**Parameters:**
- `swf_path` (required): Absolute path to SWF file
- `class_names` (required): List of class names (e.g., `['com.example.Main']`)
- `output_dir` (required): Directory for extracted classes
- `timeout` (optional): Timeout in seconds (default: 60)

### 3. `list_symbols`
List all ActionScript classes and symbols in a SWF file. Great for exploring a SWF before full decompilation.

**Parameters:**
- `swf_path` (required): Absolute path to SWF file

**Returns:** Structured JSON with packages, classes, and total count

### 4. `extract_assets`
Extract images, sounds, fonts, shapes, movie clips, and binary data from SWF.

**Parameters:**
- `swf_path` (required): Absolute path to SWF file
- `output_dir` (required): Directory for extracted assets
- `asset_types` (optional): Types to extract - `image`, `sound`, `font`, `shape`, `movie`, `binaryData`, `all` (default: `["all"]`)
- `timeout` (optional): Timeout in seconds (default: 60)

### 5. `get_swf_metadata`
Extract SWF header information (dimensions, frame rate, compression, etc.). Fast and doesn't require decompilation.

**Parameters:**
- `swf_path` (required): Absolute path to SWF file

**Returns:** JSON with version, width, height, frame_rate, frame_count, compression

### 6. `deobfuscate`
Run FFDec's deobfuscation algorithms to remove obfuscation and anti-decompilation tricks.

**Parameters:**
- `swf_path` (required): Absolute path to obfuscated SWF
- `output_path` (required): Path for deobfuscated SWF
- `level` (optional): Deobfuscation level - `traps`, `deadcode`, `max` (default: `max`)
- `timeout` (optional): Timeout in seconds (default: 60)

## Quick Start

**Prerequisites:** Python 3.10+ and Java (for running the FFDec JAR).

### Claude Code

```bash
claude mcp add ffdecmcp -- uvx ffdecmcp
```

That's it. On first run, FFDec will be auto-downloaded if not already installed.

### Claude Desktop

Add to your config file (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "ffdecmcp": {
      "command": "uvx",
      "args": ["ffdecmcp"]
    }
  }
}
```

### Standalone

```bash
# Just run it - FFDec will be auto-downloaded to ~/.ffdecmcp/ if needed
uvx ffdecmcp

# Or point to an existing FFDec installation
uvx ffdecmcp --ffdec-path /path/to/ffdec.jar
```

## Installation

No installation is required when using `uvx`. For a permanent install:

```bash
uv pip install ffdecmcp
# or
pip install ffdecmcp
```

### FFDec

FFDec is automatically downloaded on first run if not found. You can also install it manually.

The server finds FFDec in this order:

1. `--ffdec-path` CLI arg / `FFDEC_PATH` env var
2. Previously auto-downloaded JAR (`~/.ffdecmcp/ffdec.jar`)
3. Common install locations and PATH
5. Auto-download from GitHub

### CLI Options

```
ffdecmcp [--ffdec-path PATH] [--timeout SECONDS]
```

| Option | Env Var | Description |
|---|---|---|
| `--ffdec-path` | `FFDEC_PATH` | Path to FFDec (JAR, native binary, or WSL path) |
| `--timeout` | `FFDEC_TIMEOUT` | Default timeout in seconds (default: 60) |

CLI arguments take precedence over environment variables.

### Development

```bash
git clone https://github.com/sublimnl/ffdecmcp.git
cd ffdecmcp
uv pip install -e ".[dev]"
```

### Example Usage in Claude

```
You: Can you analyze this SWF file for me?
Path: C:\Users\foo\game.swf

Claude will:
1. Use get_swf_metadata to check dimensions, version, etc.
2. Use list_symbols to see what classes are present
3. Use decompile_swf to extract all ActionScript code
4. Analyze the decompiled code and provide insights
```

## References

- **FFDec**: https://github.com/jindrapetrik/jpexs-decompiler
- **FFDec CLI Docs**: https://github.com/jindrapetrik/jpexs-decompiler/wiki/Commandline-arguments
- **Model Context Protocol**: https://modelcontextprotocol.io
- **FastMCP**: https://github.com/jlowin/fastmcp

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please open an issue or PR on GitHub.

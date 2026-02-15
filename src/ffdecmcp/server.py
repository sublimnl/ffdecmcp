"""FastMCP server with FFDec tools."""

import logging
import sys
from typing import Any, Optional

from fastmcp import FastMCP

from .ffdec import FFDecError, FFDecWrapper

# Configure logging to stderr (critical for STDIO transport)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("ffdecmcp")

# Lazy-initialized FFDec wrapper (config must be ready before first tool call)
_ffdec: Optional[FFDecWrapper] = None


def get_ffdec() -> FFDecWrapper:
    """Get or create FFDec wrapper instance."""
    global _ffdec
    if _ffdec is None:
        _ffdec = FFDecWrapper()
    return _ffdec


@mcp.tool()
def decompile_swf(
    swf_path: str,
    output_dir: str,
    timeout: Optional[int] = None,
) -> dict[str, Any]:
    """
    Decompile all ActionScript code from a SWF file.

    This tool extracts and decompiles all ActionScript (AS2/AS3) code from a Flash SWF file,
    organizing the output into a directory structure that mirrors the package hierarchy.

    Args:
        swf_path: Absolute path to the SWF file to decompile
        output_dir: Directory where decompiled scripts will be saved
        timeout: Optional timeout in seconds (default: 60)

    Returns:
        Dictionary with:
        - success: Whether decompilation succeeded
        - swf_path: Input SWF file path
        - output_dir: Output directory path
        - script_count: Number of ActionScript files extracted
        - message: Success message

    Example:
        >>> decompile_swf("/path/to/game.swf", "/path/to/output")
        {
            "success": true,
            "swf_path": "/path/to/game.swf",
            "output_dir": "/path/to/output",
            "script_count": 42,
            "message": "Successfully decompiled 42 ActionScript files"
        }
    """
    try:
        logger.info(f"Decompiling SWF: {swf_path} -> {output_dir}")
        result = get_ffdec().decompile_swf(swf_path, output_dir, timeout)
        logger.info(f"Decompilation complete: {result['script_count']} files")
        return result
    except FFDecError as e:
        logger.error(f"Decompilation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Decompilation failed: {e}",
        }
    except Exception as e:
        logger.error(f"Unexpected error during decompilation: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Unexpected error: {e}",
        }


@mcp.tool()
def extract_actionscript(
    swf_path: str,
    class_names: list[str],
    output_dir: str,
    timeout: Optional[int] = None,
) -> dict[str, Any]:
    """
    Extract specific ActionScript classes by name from a SWF file.

    This tool selectively extracts only the specified ActionScript classes (AS3 only),
    which is faster than full decompilation when you only need specific classes.

    Args:
        swf_path: Absolute path to the SWF file
        class_names: List of fully-qualified class names to extract (e.g., ['com.example.Main', 'com.example.Utils'])
        output_dir: Directory where extracted classes will be saved
        timeout: Optional timeout in seconds (default: 60)

    Returns:
        Dictionary with:
        - success: Whether extraction succeeded
        - swf_path: Input SWF file path
        - output_dir: Output directory path
        - requested_classes: List of requested class names
        - extracted_files: Number of files extracted
        - message: Success message

    Example:
        >>> extract_actionscript("/path/to/game.swf", ["com.game.Main", "com.game.Player"], "/path/to/output")
        {
            "success": true,
            "swf_path": "/path/to/game.swf",
            "output_dir": "/path/to/output",
            "requested_classes": ["com.game.Main", "com.game.Player"],
            "extracted_files": 2,
            "message": "Successfully extracted 2 ActionScript files"
        }
    """
    try:
        logger.info(
            f"Extracting ActionScript classes from {swf_path}: {class_names}"
        )
        result = get_ffdec().extract_actionscript(swf_path, class_names, output_dir, timeout)
        logger.info(f"Extraction complete: {result['extracted_files']} files")
        return result
    except FFDecError as e:
        logger.error(f"ActionScript extraction failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"ActionScript extraction failed: {e}",
        }
    except Exception as e:
        logger.error(
            f"Unexpected error during ActionScript extraction: {e}", exc_info=True
        )
        return {
            "success": False,
            "error": str(e),
            "message": f"Unexpected error: {e}",
        }


@mcp.tool()
def list_symbols(swf_path: str) -> dict[str, Any]:
    """
    List all ActionScript classes and symbols in a SWF file.

    This tool provides an overview of the ActionScript structure without decompiling,
    showing packages, classes, and the total symbol count. Useful for exploring a SWF
    before full decompilation.

    Args:
        swf_path: Absolute path to the SWF file

    Returns:
        Dictionary with:
        - success: Whether listing succeeded
        - type: ActionScript type (AS2, AS3, or Unknown)
        - packages: Dictionary mapping package names to class lists
        - classes: Complete list of fully-qualified class names
        - total_symbols: Total number of classes found
        - message: Summary message

    Example:
        >>> list_symbols("/path/to/game.swf")
        {
            "success": true,
            "type": "AS3",
            "packages": {
                "com.game": ["Main", "Player", "Enemy"],
                "com.game.utils": ["Vector2D", "Math"]
            },
            "classes": ["com.game.Main", "com.game.Player", ...],
            "total_symbols": 5,
            "message": "Found 5 AS3 classes in 2 packages"
        }
    """
    try:
        logger.info(f"Listing symbols in SWF: {swf_path}")
        result = get_ffdec().list_symbols(swf_path)
        logger.info(f"Symbol listing complete: {result['total_symbols']} symbols")
        return result
    except FFDecError as e:
        logger.error(f"Symbol listing failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Symbol listing failed: {e}",
        }
    except Exception as e:
        logger.error(f"Unexpected error during symbol listing: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Unexpected error: {e}",
        }


@mcp.tool()
def extract_assets(
    swf_path: str,
    output_dir: str,
    asset_types: Optional[list[str]] = None,
    timeout: Optional[int] = None,
) -> dict[str, Any]:
    """
    Extract images, sounds, fonts, and other assets from a SWF file.

    This tool extracts non-code assets from a SWF file, including images, sounds,
    fonts, shapes, movie clips, and binary data.

    Args:
        swf_path: Absolute path to the SWF file
        output_dir: Directory where extracted assets will be saved
        asset_types: Optional list of asset types to extract. Valid types: 'image', 'sound', 'font', 'shape', 'movie', 'binaryData', 'all' (default: ['all'])
        timeout: Optional timeout in seconds (default: 60)

    Returns:
        Dictionary with:
        - success: Whether extraction succeeded
        - swf_path: Input SWF file path
        - output_dir: Output directory path
        - asset_types: List of asset types extracted
        - extracted_count: Number of assets extracted
        - message: Success message

    Example:
        >>> extract_assets("/path/to/game.swf", "/path/to/output", asset_types=["image", "sound"])
        {
            "success": true,
            "swf_path": "/path/to/game.swf",
            "output_dir": "/path/to/output",
            "asset_types": ["image", "sound"],
            "extracted_count": 127,
            "message": "Successfully extracted 127 assets"
        }
    """
    try:
        logger.info(
            f"Extracting assets from {swf_path}: types={asset_types or ['all']}"
        )
        result = get_ffdec().extract_assets(swf_path, output_dir, asset_types, timeout)
        logger.info(f"Asset extraction complete: {result['extracted_count']} files")
        return result
    except FFDecError as e:
        logger.error(f"Asset extraction failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Asset extraction failed: {e}",
        }
    except Exception as e:
        logger.error(f"Unexpected error during asset extraction: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Unexpected error: {e}",
        }


@mcp.tool()
def get_swf_metadata(swf_path: str) -> dict[str, Any]:
    """
    Extract metadata from a SWF file's header.

    This tool reads the SWF file header to extract basic metadata like dimensions,
    frame rate, frame count, compression type, and Flash version. This is fast and
    doesn't require decompilation.

    Args:
        swf_path: Absolute path to the SWF file

    Returns:
        Dictionary with metadata including:
        - success: Whether extraction succeeded
        - swf_path: Input SWF file path
        - version: Flash version number
        - width: Stage width in pixels
        - height: Stage height in pixels
        - frame_rate: Frames per second
        - frame_count: Total number of frames
        - compression: Compression type (e.g., 'zlib', 'lzma', 'none')
        - Additional header fields as available

    Example:
        >>> get_swf_metadata("/path/to/game.swf")
        {
            "success": true,
            "swf_path": "/path/to/game.swf",
            "version": 10,
            "width": 800,
            "height": 600,
            "frame_rate": 30,
            "frame_count": 1,
            "compression": "zlib"
        }
    """
    try:
        logger.info(f"Extracting metadata from SWF: {swf_path}")
        result = get_ffdec().get_swf_metadata(swf_path)
        logger.info(f"Metadata extraction complete")
        return result
    except FFDecError as e:
        logger.error(f"Metadata extraction failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Metadata extraction failed: {e}",
        }
    except Exception as e:
        logger.error(
            f"Unexpected error during metadata extraction: {e}", exc_info=True
        )
        return {
            "success": False,
            "error": str(e),
            "message": f"Unexpected error: {e}",
        }


@mcp.tool()
def deobfuscate(
    swf_path: str,
    output_path: str,
    level: str = "max",
    timeout: Optional[int] = None,
) -> dict[str, Any]:
    """
    Deobfuscate a SWF file by removing obfuscation techniques.

    This tool runs FFDec's deobfuscation algorithms to remove common obfuscation
    techniques like dead code, traps, and other anti-decompilation tricks. The
    output is a cleaner SWF file that's easier to decompile and analyze.

    Args:
        swf_path: Absolute path to the obfuscated SWF file
        output_path: Path where the deobfuscated SWF will be saved
        level: Deobfuscation level - 'traps' (remove traps only), 'deadcode' (remove dead code), 'max' (full deobfuscation, default)
        timeout: Optional timeout in seconds (default: 60)

    Returns:
        Dictionary with:
        - success: Whether deobfuscation succeeded
        - input_path: Input SWF file path
        - output_path: Output SWF file path
        - level: Deobfuscation level used
        - message: Success message

    Example:
        >>> deobfuscate("/path/to/obfuscated.swf", "/path/to/clean.swf", level="max")
        {
            "success": true,
            "input_path": "/path/to/obfuscated.swf",
            "output_path": "/path/to/clean.swf",
            "level": "max",
            "message": "Successfully deobfuscated SWF at level 'max'"
        }
    """
    try:
        logger.info(
            f"Deobfuscating SWF: {swf_path} -> {output_path} (level={level})"
        )
        result = get_ffdec().deobfuscate(swf_path, output_path, level, timeout)
        logger.info(f"Deobfuscation complete")
        return result
    except FFDecError as e:
        logger.error(f"Deobfuscation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Deobfuscation failed: {e}",
        }
    except Exception as e:
        logger.error(f"Unexpected error during deobfuscation: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Unexpected error: {e}",
        }

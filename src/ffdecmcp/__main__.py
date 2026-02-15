"""Entry point for ffdecmcp server."""

import argparse
import logging
import os
import sys

from dotenv import load_dotenv

# Configure logging to stderr (critical for STDIO transport)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for ffdecmcp server."""
    parser = argparse.ArgumentParser(
        prog="ffdecmcp",
        description="MCP server for JPEXS Free Flash Decompiler (FFDec)",
    )
    parser.add_argument(
        "--ffdec-path",
        metavar="PATH",
        help="Path to FFDec (JAR file, native binary, or WSL path). "
        "Can also be set via FFDEC_PATH env var.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        metavar="SECONDS",
        help="Default timeout for FFDec operations in seconds (default: 60). "
        "Can also be set via FFDEC_TIMEOUT env var.",
    )
    args = parser.parse_args()

    # CLI args take precedence over env vars
    if args.ffdec_path:
        os.environ["FFDEC_PATH"] = args.ffdec_path
    if args.timeout is not None:
        os.environ["FFDEC_TIMEOUT"] = str(args.timeout)

    try:
        # Load .env file (env vars and CLI args take precedence)
        load_dotenv()

        logger.info("Starting ffdecmcp server...")

        # Import after environment is loaded
        from .config import get_config
        from .server import mcp

        # Verify FFDec configuration on startup - fail fast if not found
        try:
            config = get_config()
            logger.info(
                f"FFDec detected: mode={config.mode.value}, path={config.path}, timeout={config.timeout}s"
            )
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        # Run the FastMCP server
        logger.info("ffdecmcp server started successfully")
        mcp.run()

    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

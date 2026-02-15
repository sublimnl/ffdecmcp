"""FFDec configuration and detection."""

import json
import os
import platform
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError

import logging

# Configure logging to stderr (critical for STDIO transport)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


class FFDecMode(Enum):
    """FFDec execution modes."""

    WSL = "wsl"  # WSL on Windows (fastest, 10-20x faster than GUI)
    JAR = "jar"  # Java JAR file (cross-platform)
    NATIVE = "native"  # Native binary (ffdec.bat, ffdec-cli.exe)


@dataclass
class FFDecConfig:
    """FFDec configuration."""

    mode: FFDecMode
    path: str
    timeout: int = 60

    def __post_init__(self):
        """Validate configuration."""
        if self.timeout <= 0:
            raise ValueError(f"Timeout must be positive, got {self.timeout}")


class FFDecDetector:
    """Detects and configures FFDec installation."""

    # Default install directory for auto-downloaded JAR
    INSTALL_DIR = Path.home() / ".ffdecmcp"

    # Common JAR locations
    JAR_LOCATIONS = [
        str(INSTALL_DIR / "ffdec.jar"),
        "C:\\Program Files\\FFDec\\ffdec.jar",
        "C:\\Program Files (x86)\\FFDec\\ffdec.jar",
        "/usr/local/lib/ffdec/ffdec.jar",
        "/opt/ffdec/ffdec.jar",
        str(Path.home() / "ffdec" / "ffdec.jar"),
    ]

    GITHUB_API_LATEST = "https://api.github.com/repos/jindrapetrik/jpexs-decompiler/releases/latest"

    # WSL ffdec locations
    WSL_LOCATIONS = ["/usr/local/bin/ffdec", "/usr/bin/ffdec"]

    @staticmethod
    def is_windows() -> bool:
        """Check if running on Windows."""
        return platform.system() == "Windows"

    @staticmethod
    def check_wsl_available() -> bool:
        """Check if WSL is available on Windows."""
        if not FFDecDetector.is_windows():
            return False

        try:
            result = subprocess.run(
                ["wsl", "--status"],
                capture_output=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if FFDecDetector.is_windows() else 0,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    @staticmethod
    def check_wsl_ffdec() -> Optional[str]:
        """Check for ffdec in WSL."""
        for location in FFDecDetector.WSL_LOCATIONS:
            try:
                result = subprocess.run(
                    ["wsl", "test", "-f", location, "&&", "echo", "exists"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW if FFDecDetector.is_windows() else 0,
                )
                if result.returncode == 0 and "exists" in result.stdout:
                    logger.info(f"Found FFDec in WSL at {location}")
                    return location
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        return None

    @staticmethod
    def check_jar_exists(path: str) -> bool:
        """Check if JAR file exists."""
        return Path(path).is_file()

    @staticmethod
    def find_jar() -> Optional[str]:
        """Find ffdec.jar in common locations."""
        # Check environment variable first
        env_path = os.environ.get("FFDEC_JAR_PATH")
        if env_path and FFDecDetector.check_jar_exists(env_path):
            logger.info(f"Found FFDec JAR via FFDEC_JAR_PATH: {env_path}")
            return env_path

        # Check common locations
        for location in FFDecDetector.JAR_LOCATIONS:
            if FFDecDetector.check_jar_exists(location):
                logger.info(f"Found FFDec JAR at {location}")
                return location

        return None

    @staticmethod
    def check_native_binary() -> Optional[str]:
        """Check for native ffdec binary in PATH."""
        binaries = ["ffdec", "ffdec.bat", "ffdec-cli.exe"]

        for binary in binaries:
            try:
                result = subprocess.run(
                    ["where" if FFDecDetector.is_windows() else "which", binary],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW if FFDecDetector.is_windows() else 0,
                )
                if result.returncode == 0:
                    path = result.stdout.strip().split("\n")[0]
                    logger.info(f"Found native FFDec binary at {path}")
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        return None

    @classmethod
    def download_latest(cls) -> Optional[str]:
        """
        Download the latest FFDec release JAR from GitHub.

        Returns:
            Path to downloaded ffdec.jar, or None if download failed
        """
        try:
            logger.info("Downloading latest FFDec release from GitHub...")
            print("FFDec not found locally. Downloading latest release...", file=sys.stderr)

            # Query GitHub API for latest release
            req = Request(cls.GITHUB_API_LATEST, headers={"User-Agent": "ffdecmcp"})
            with urlopen(req, timeout=15) as resp:
                release = json.loads(resp.read())

            version = release.get("tag_name", "unknown")
            logger.info(f"Latest FFDec release: {version}")

            # Find the zip asset (e.g. "ffdec_21.0.2.zip")
            zip_asset = None
            for asset in release.get("assets", []):
                name = asset["name"]
                if name.startswith("ffdec_") and name.endswith(".zip"):
                    zip_asset = asset
                    break

            if not zip_asset:
                logger.error("Could not find FFDec zip asset in release")
                return None

            download_url = zip_asset["browser_download_url"]
            zip_size = zip_asset.get("size", 0)
            size_mb = zip_size / (1024 * 1024) if zip_size else 0
            print(f"Downloading {zip_asset['name']} ({size_mb:.1f} MB)...", file=sys.stderr)

            # Download the zip
            req = Request(download_url, headers={"User-Agent": "ffdecmcp"})
            with urlopen(req, timeout=120) as resp:
                zip_data = resp.read()

            # Extract to install directory
            install_dir = cls.INSTALL_DIR
            install_dir.mkdir(parents=True, exist_ok=True)

            import io
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                # Find ffdec.jar and lib/ entries in the zip
                jar_entry = None
                lib_entries = []
                for entry in zf.namelist():
                    # Skip directories
                    if entry.endswith("/"):
                        continue
                    basename = entry.split("/")[-1]
                    if basename == "ffdec.jar":
                        jar_entry = entry
                    # Match lib/ at root or inside a subdirectory (e.g. "lib/foo.jar" or "ffdec_25/lib/foo.jar")
                    elif "lib/" in entry and basename.endswith(".jar"):
                        lib_entries.append(entry)

                if not jar_entry:
                    logger.error("ffdec.jar not found in downloaded zip")
                    return None

                # Extract the JAR
                jar_dest = install_dir / "ffdec.jar"
                with zf.open(jar_entry) as src, open(jar_dest, "wb") as dst:
                    dst.write(src.read())

                # Extract lib/ JARs (required dependencies)
                lib_dir = install_dir / "lib"
                lib_dir.mkdir(exist_ok=True)
                for entry in lib_entries:
                    basename = entry.split("/")[-1]
                    with zf.open(entry) as src, open(lib_dir / basename, "wb") as dst:
                        dst.write(src.read())

            jar_path = str(jar_dest)
            print(f"FFDec {version} installed to {install_dir}", file=sys.stderr)
            logger.info(f"FFDec downloaded and extracted to {jar_path}")
            return jar_path

        except (URLError, OSError, json.JSONDecodeError, zipfile.BadZipFile) as e:
            logger.error(f"Failed to download FFDec: {e}")
            print(f"Failed to download FFDec: {e}", file=sys.stderr)
            return None

    @classmethod
    def detect(cls) -> FFDecConfig:
        """
        Detect FFDec installation.

        Priority order:
        1. FFDEC_PATH environment variable
        2. WSL (Windows only, fastest)
        3. JAR file
        4. Native binary

        Returns:
            FFDecConfig with detected mode and path

        Raises:
            RuntimeError: If FFDec cannot be found
        """
        # Get timeout from environment or use default
        timeout = int(os.environ.get("FFDEC_TIMEOUT", "60"))

        # Check for forced mode
        forced_mode = os.environ.get("FFDEC_MODE", "").lower()

        # Priority 1: Check FFDEC_PATH environment variable
        env_path = os.environ.get("FFDEC_PATH")
        if env_path:
            env_path = env_path.strip()
            logger.info(f"Using FFDEC_PATH: {env_path}")

            # Determine mode based on path
            if env_path.startswith("/") and cls.is_windows():
                # WSL path on Windows
                return FFDecConfig(mode=FFDecMode.WSL, path=env_path, timeout=timeout)
            elif env_path.endswith(".jar"):
                return FFDecConfig(mode=FFDecMode.JAR, path=env_path, timeout=timeout)
            else:
                return FFDecConfig(mode=FFDecMode.NATIVE, path=env_path, timeout=timeout)

        # Priority 2: WSL detection (Windows only)
        if (forced_mode == "wsl" or not forced_mode) and cls.is_windows():
            if cls.check_wsl_available():
                wsl_path = cls.check_wsl_ffdec()
                if wsl_path:
                    return FFDecConfig(mode=FFDecMode.WSL, path=wsl_path, timeout=timeout)

        # Priority 3: JAR detection
        if forced_mode == "jar" or not forced_mode:
            jar_path = cls.find_jar()
            if jar_path:
                return FFDecConfig(mode=FFDecMode.JAR, path=jar_path, timeout=timeout)

        # Priority 4: Native binary
        if forced_mode == "native" or not forced_mode:
            native_path = cls.check_native_binary()
            if native_path:
                return FFDecConfig(
                    mode=FFDecMode.NATIVE, path=native_path, timeout=timeout
                )

        # Not found locally - try downloading
        jar_path = cls.download_latest()
        if jar_path:
            return FFDecConfig(mode=FFDecMode.JAR, path=jar_path, timeout=timeout)

        # Download also failed - raise with helpful message
        raise RuntimeError(
            "FFDec not found and automatic download failed.\n\n"
            "Please provide the path to FFDec:\n"
            "  ffdecmcp --ffdec-path /path/to/ffdec.jar\n\n"
            "Or set the FFDEC_PATH environment variable.\n\n"
            "Installation options:\n"
            "1. JAR: Download from https://github.com/jindrapetrik/jpexs-decompiler/releases\n"
            "2. WSL (Windows, fastest): Install in WSL with 'sudo apt install ffdec'\n"
            "3. Native: Install system package or add to PATH"
        )


# Singleton config instance
_config: Optional[FFDecConfig] = None


def get_config() -> FFDecConfig:
    """Get or create FFDec configuration."""
    global _config
    if _config is None:
        _config = FFDecDetector.detect()
        logger.info(f"FFDec configuration: mode={_config.mode.value}, path={_config.path}")
    return _config


def reset_config():
    """Reset configuration (useful for testing)."""
    global _config
    _config = None

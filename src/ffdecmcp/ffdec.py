"""FFDec execution wrapper."""

import json
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from .config import FFDecConfig, FFDecMode, get_config
from .utils import normalize_path, validate_output_dir, validate_swf_path

# Configure logging to stderr
logger = logging.getLogger(__name__)


class FFDecError(Exception):
    """Base exception for FFDec errors."""

    pass


class FFDecTimeoutError(FFDecError):
    """Raised when FFDec execution times out."""

    pass


class FFDecExecutionError(FFDecError):
    """Raised when FFDec execution fails."""

    pass


class FFDecWrapper:
    """Wrapper for executing FFDec commands."""

    def __init__(self, config: Optional[FFDecConfig] = None):
        """
        Initialize FFDec wrapper.

        Args:
            config: FFDec configuration (auto-detected if not provided)
        """
        self.config = config or get_config()
        logger.info(
            f"FFDecWrapper initialized with mode={self.config.mode.value}, "
            f"path={self.config.path}"
        )

    def _build_command(self, args: list[str]) -> list[str]:
        """
        Build command based on execution mode.

        Args:
            args: FFDec arguments

        Returns:
            Complete command list
        """
        if self.config.mode == FFDecMode.WSL:
            # WSL execution: wsl <ffdec_path> <args>
            return ["wsl", self.config.path] + args

        elif self.config.mode == FFDecMode.JAR:
            # JAR execution: java -jar <jar_path> <args>
            # Use absolute path so cwd can be set to jar's directory (for classpath resolution)
            jar_path = str(Path(self.config.path).resolve())
            return ["java", "-Djava.awt.headless=true", "-jar", jar_path] + args

        else:  # NATIVE
            # Native execution: <binary_path> <args>
            return [self.config.path] + args

    def _execute(
        self,
        args: list[str],
        timeout: Optional[int] = None,
        check_returncode: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Execute FFDec command.

        Args:
            args: FFDec arguments
            timeout: Timeout in seconds (uses config default if not specified)
            check_returncode: If True, raise exception on non-zero return code

        Returns:
            CompletedProcess result

        Raises:
            FFDecTimeoutError: If execution times out
            FFDecExecutionError: If execution fails
        """
        timeout = timeout or self.config.timeout
        command = self._build_command(args)

        logger.info(f"Executing FFDec command: {' '.join(command)}")

        # Set cwd to jar directory for classpath resolution in JAR mode
        cwd = None
        if self.config.mode == FFDecMode.JAR:
            cwd = str(Path(self.config.path).resolve().parent)

        try:
            # Execute command
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW
                    if sys.platform == "win32"
                    else 0
                ),
            )

            # Log output
            if result.stdout:
                logger.debug(f"FFDec stdout: {result.stdout}")
            if result.stderr:
                logger.debug(f"FFDec stderr: {result.stderr}")

            # Check return code
            if check_returncode and result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                raise FFDecExecutionError(
                    f"FFDec command failed with return code {result.returncode}: {error_msg}"
                )

            return result

        except subprocess.TimeoutExpired as e:
            raise FFDecTimeoutError(
                f"FFDec command timed out after {timeout} seconds. "
                f"Try increasing FFDEC_TIMEOUT or simplifying the operation."
            ) from e

        except FileNotFoundError as e:
            raise FFDecExecutionError(
                f"FFDec executable not found: {self.config.path}. "
                f"Please check FFDEC_PATH configuration."
            ) from e

        except Exception as e:
            raise FFDecExecutionError(f"Failed to execute FFDec: {e}") from e

    def _normalize_paths(self, *paths: str) -> list[str]:
        """
        Normalize paths for FFDec execution.

        Args:
            paths: Paths to normalize

        Returns:
            List of normalized paths
        """
        use_wsl = self.config.mode == FFDecMode.WSL
        return [normalize_path(p, for_wsl=use_wsl) for p in paths]

    def decompile_swf(
        self, swf_path: str, output_dir: str, timeout: Optional[int] = None
    ) -> dict[str, Any]:
        """
        Decompile all ActionScript from SWF file.

        Args:
            swf_path: Path to SWF file
            output_dir: Output directory for decompiled scripts
            timeout: Timeout in seconds

        Returns:
            Result dictionary with status and details

        Raises:
            FFDecError: If decompilation fails
        """
        # Validate inputs
        is_valid, error = validate_swf_path(swf_path)
        if not is_valid:
            raise FFDecError(error)

        is_valid, error = validate_output_dir(output_dir, create=True)
        if not is_valid:
            raise FFDecError(error)

        # Normalize paths
        swf_norm, output_norm = self._normalize_paths(swf_path, output_dir)

        # Build command: ffdec -timeout <timeout> -onerror ignore -export script <output_dir> <swf_path>
        timeout_val = timeout or self.config.timeout
        args = [
            "-timeout",
            str(timeout_val),
            "-onerror",
            "ignore",
            "-export",
            "script",
            output_norm,
            swf_norm,
        ]

        # Execute
        try:
            result = self._execute(args, timeout=timeout_val)

            # Count output files
            output_path = Path(output_dir)
            script_files = list(output_path.rglob("*.as"))

            return {
                "success": True,
                "swf_path": swf_path,
                "output_dir": output_dir,
                "script_count": len(script_files),
                "message": f"Successfully decompiled {len(script_files)} ActionScript files",
            }

        except FFDecError:
            raise
        except Exception as e:
            raise FFDecExecutionError(f"Decompilation failed: {e}") from e

    def extract_actionscript(
        self,
        swf_path: str,
        class_names: list[str],
        output_dir: str,
        timeout: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Extract specific ActionScript classes by name.

        Args:
            swf_path: Path to SWF file
            class_names: List of class names to extract
            output_dir: Output directory for extracted classes
            timeout: Timeout in seconds

        Returns:
            Result dictionary with status and details

        Raises:
            FFDecError: If extraction fails
        """
        # Validate inputs
        if not class_names:
            raise FFDecError("No class names provided")

        is_valid, error = validate_swf_path(swf_path)
        if not is_valid:
            raise FFDecError(error)

        is_valid, error = validate_output_dir(output_dir, create=True)
        if not is_valid:
            raise FFDecError(error)

        # Normalize paths
        swf_norm, output_norm = self._normalize_paths(swf_path, output_dir)

        # Build command: ffdec -selectclass <classes> -export script <output_dir> <swf_path>
        timeout_val = timeout or self.config.timeout
        class_list = ",".join(class_names)

        args = [
            "-selectclass",
            class_list,
            "-export",
            "script",
            output_norm,
            swf_norm,
        ]

        # Execute
        try:
            result = self._execute(args, timeout=timeout_val)

            # Count output files
            output_path = Path(output_dir)
            script_files = list(output_path.rglob("*.as"))

            return {
                "success": True,
                "swf_path": swf_path,
                "output_dir": output_dir,
                "requested_classes": class_names,
                "extracted_files": len(script_files),
                "message": f"Successfully extracted {len(script_files)} ActionScript files",
            }

        except FFDecError:
            raise
        except Exception as e:
            raise FFDecExecutionError(f"ActionScript extraction failed: {e}") from e

    def list_symbols(self, swf_path: str) -> dict[str, Any]:
        """
        List all classes and symbols in SWF file.

        Args:
            swf_path: Path to SWF file

        Returns:
            Dictionary with packages, classes, and symbols

        Raises:
            FFDecError: If listing fails
        """
        # Validate input
        is_valid, error = validate_swf_path(swf_path)
        if not is_valid:
            raise FFDecError(error)

        # Normalize path
        swf_norm = self._normalize_paths(swf_path)[0]

        # Try AS3 first
        try:
            args = ["-dumpAS3", swf_norm]
            result = self._execute(args, check_returncode=False)

            if result.returncode == 0 and result.stdout:
                return self._parse_symbol_dump(result.stdout, "AS3")

        except FFDecError:
            pass

        # Fallback to AS2
        try:
            args = ["-dumpAS2", swf_norm]
            result = self._execute(args, check_returncode=False)

            if result.returncode == 0 and result.stdout:
                return self._parse_symbol_dump(result.stdout, "AS2")

        except FFDecError:
            pass

        # If both failed, return empty result
        return {
            "success": True,
            "swf_path": swf_path,
            "type": "Unknown",
            "packages": {},
            "classes": [],
            "total_symbols": 0,
            "message": "No ActionScript symbols found (may not contain AS2/AS3 code)",
        }

    def _parse_symbol_dump(self, dump: str, as_type: str) -> dict[str, Any]:
        """
        Parse FFDec symbol dump output.

        Args:
            dump: Raw dump output
            as_type: ActionScript type (AS2 or AS3)

        Returns:
            Parsed symbol dictionary
        """
        packages = {}
        classes = []

        # Parse lines for class definitions
        # Format: "class com.example.MyClass" or "package com.example { class MyClass }"
        for line in dump.split("\n"):
            line = line.strip()

            # Match class definitions
            class_match = re.search(r"class\s+([\w.]+)", line)
            if class_match:
                full_class = class_match.group(1)
                classes.append(full_class)

                # Extract package
                if "." in full_class:
                    package = ".".join(full_class.split(".")[:-1])
                    class_name = full_class.split(".")[-1]
                else:
                    package = "(default)"
                    class_name = full_class

                if package not in packages:
                    packages[package] = []
                packages[package].append(class_name)

        return {
            "success": True,
            "type": as_type,
            "packages": packages,
            "classes": classes,
            "total_symbols": len(classes),
            "message": f"Found {len(classes)} {as_type} classes in {len(packages)} packages",
        }

    def extract_assets(
        self,
        swf_path: str,
        output_dir: str,
        asset_types: Optional[list[str]] = None,
        timeout: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Extract assets from SWF file.

        Args:
            swf_path: Path to SWF file
            output_dir: Output directory for extracted assets
            asset_types: List of asset types (image, sound, font, shape, movie, binaryData, all)
            timeout: Timeout in seconds

        Returns:
            Result dictionary with status and details

        Raises:
            FFDecError: If extraction fails
        """
        # Validate inputs
        is_valid, error = validate_swf_path(swf_path)
        if not is_valid:
            raise FFDecError(error)

        is_valid, error = validate_output_dir(output_dir, create=True)
        if not is_valid:
            raise FFDecError(error)

        # Default to all assets
        if not asset_types:
            asset_types = ["all"]

        # Validate asset types
        valid_types = {"image", "sound", "font", "shape", "movie", "binaryData", "all"}
        invalid = set(asset_types) - valid_types
        if invalid:
            raise FFDecError(f"Invalid asset types: {invalid}. Valid: {valid_types}")

        # Normalize paths
        swf_norm, output_norm = self._normalize_paths(swf_path, output_dir)

        # Build command: ffdec -export <types> <output_dir> <swf_path>
        timeout_val = timeout or self.config.timeout

        # Build export arguments
        args = []
        for asset_type in asset_types:
            args.extend(["-export", asset_type])
        args.extend([output_norm, swf_norm])

        # Execute
        try:
            result = self._execute(args, timeout=timeout_val)

            # Count output files
            output_path = Path(output_dir)
            asset_files = [
                f for f in output_path.rglob("*") if f.is_file()
            ]

            return {
                "success": True,
                "swf_path": swf_path,
                "output_dir": output_dir,
                "asset_types": asset_types,
                "extracted_count": len(asset_files),
                "message": f"Successfully extracted {len(asset_files)} assets",
            }

        except FFDecError:
            raise
        except Exception as e:
            raise FFDecExecutionError(f"Asset extraction failed: {e}") from e

    def get_swf_metadata(self, swf_path: str) -> dict[str, Any]:
        """
        Extract SWF header metadata.

        Args:
            swf_path: Path to SWF file

        Returns:
            Dictionary with SWF metadata

        Raises:
            FFDecError: If metadata extraction fails
        """
        # Validate input
        is_valid, error = validate_swf_path(swf_path)
        if not is_valid:
            raise FFDecError(error)

        # Normalize path
        swf_norm = self._normalize_paths(swf_path)[0]

        # Build command: ffdec -header <swf_path>
        args = ["-header", swf_norm]

        # Execute
        try:
            result = self._execute(args)

            # Parse header output
            metadata = self._parse_header(result.stdout)
            metadata["success"] = True
            metadata["swf_path"] = swf_path

            return metadata

        except FFDecError:
            raise
        except Exception as e:
            raise FFDecExecutionError(f"Metadata extraction failed: {e}") from e

    def _parse_header(self, header: str) -> dict[str, Any]:
        """
        Parse FFDec header output.

        Args:
            header: Raw header output

        Returns:
            Parsed metadata dictionary
        """
        metadata = {}

        # Parse header lines
        # Format: "key=value" (with optional [header] section marker)
        for line in header.split("\n"):
            line = line.strip()
            if line.startswith("[") or not line:
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip().lower()
                value = value.strip()

                # Convert numeric values
                if value.isdigit():
                    value = int(value)
                elif re.match(r"^\d+\.\d+$", value):
                    value = float(value)

                metadata[key] = value

        return metadata

    def deobfuscate(
        self,
        swf_path: str,
        output_path: str,
        level: str = "max",
        timeout: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Deobfuscate SWF file.

        Args:
            swf_path: Path to obfuscated SWF file
            output_path: Path for deobfuscated SWF
            level: Deobfuscation level (traps, deadcode, max)
            timeout: Timeout in seconds

        Returns:
            Result dictionary with status and details

        Raises:
            FFDecError: If deobfuscation fails
        """
        # Validate inputs
        is_valid, error = validate_swf_path(swf_path)
        if not is_valid:
            raise FFDecError(error)

        # Validate level
        valid_levels = {"traps", "deadcode", "max"}
        if level not in valid_levels:
            raise FFDecError(
                f"Invalid deobfuscation level: {level}. Valid: {valid_levels}"
            )

        # Ensure output directory exists
        output_dir = str(Path(output_path).parent)
        is_valid, error = validate_output_dir(output_dir, create=True)
        if not is_valid:
            raise FFDecError(error)

        # Normalize paths
        swf_norm, output_norm = self._normalize_paths(swf_path, output_path)

        # Build command: ffdec -deobfuscate <level> <input_swf> <output_swf>
        timeout_val = timeout or self.config.timeout
        args = ["-deobfuscate", level, swf_norm, output_norm]

        # Execute
        try:
            result = self._execute(args, timeout=timeout_val)

            # Check if output file was created
            if not Path(output_path).exists():
                raise FFDecExecutionError("Output file was not created")

            return {
                "success": True,
                "input_path": swf_path,
                "output_path": output_path,
                "level": level,
                "message": f"Successfully deobfuscated SWF at level '{level}'",
            }

        except FFDecError:
            raise
        except Exception as e:
            raise FFDecExecutionError(f"Deobfuscation failed: {e}") from e

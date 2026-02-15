"""Tests for MCP tools."""

import pytest
from ffdecmcp.server import (
    decompile_swf,
    extract_actionscript,
    list_symbols,
    extract_assets,
    get_swf_metadata,
    deobfuscate,
)


class TestMCPTools:
    """Test MCP tool functions."""

    def test_decompile_swf_missing_file(self):
        """Test decompile_swf with missing file."""
        result = decompile_swf.fn("/nonexistent/file.swf", "/tmp/output")
        assert result["success"] is False
        assert "error" in result

    def test_extract_actionscript_missing_file(self):
        """Test extract_actionscript with missing file."""
        result = extract_actionscript.fn(
            "/nonexistent/file.swf", ["com.test.Main"], "/tmp/output"
        )
        assert result["success"] is False
        assert "error" in result

    def test_extract_actionscript_empty_classes(self):
        """Test extract_actionscript with empty class list."""
        result = extract_actionscript.fn("/tmp/test.swf", [], "/tmp/output")
        assert result["success"] is False
        assert "error" in result

    def test_list_symbols_missing_file(self):
        """Test list_symbols with missing file."""
        result = list_symbols.fn("/nonexistent/file.swf")
        assert result["success"] is False
        assert "error" in result

    def test_extract_assets_missing_file(self):
        """Test extract_assets with missing file."""
        result = extract_assets.fn("/nonexistent/file.swf", "/tmp/output")
        assert result["success"] is False
        assert "error" in result

    def test_get_swf_metadata_missing_file(self):
        """Test get_swf_metadata with missing file."""
        result = get_swf_metadata.fn("/nonexistent/file.swf")
        assert result["success"] is False
        assert "error" in result

    def test_deobfuscate_missing_file(self):
        """Test deobfuscate with missing file."""
        result = deobfuscate.fn("/nonexistent/file.swf", "/tmp/output.swf")
        assert result["success"] is False
        assert "error" in result

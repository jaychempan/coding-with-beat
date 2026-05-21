import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cc_jukebox import mcp_client


class MCPClientConfigTest(unittest.TestCase):
    def test_configured_url_defaults_to_local_mcp_endpoint(self):
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch.object(mcp_client, "MCP_URL_FILE", Path(tmpdir) / "mcp-url"),
        ):
            self.assertEqual(mcp_client.configured_url(), mcp_client.DEFAULT_MCP_URL)

    def test_configured_url_reads_installed_mcp_url_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            url_file = Path(tmpdir) / "mcp-url"
            url_file.write_text("http://127.0.0.1:9876/mcp\n", encoding="utf-8")

            with (
                mock.patch.dict(os.environ, {}, clear=True),
                mock.patch.object(mcp_client, "MCP_URL_FILE", url_file),
            ):
                self.assertEqual(mcp_client.configured_url(), "http://127.0.0.1:9876/mcp")

    def test_configured_url_env_overrides_installed_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            url_file = Path(tmpdir) / "mcp-url"
            url_file.write_text("http://127.0.0.1:9876/mcp\n", encoding="utf-8")

            with (
                mock.patch.dict(
                    os.environ,
                    {mcp_client.MCP_URL_ENV: "http://127.0.0.1:7777/mcp"},
                    clear=True,
                ),
                mock.patch.object(mcp_client, "MCP_URL_FILE", url_file),
            ):
                self.assertEqual(mcp_client.configured_url(), "http://127.0.0.1:7777/mcp")


if __name__ == "__main__":
    unittest.main()

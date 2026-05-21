import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
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

    def test_call_tool_passes_configured_timeout_to_async_client(self):
        with (
            mock.patch.object(mcp_client, "configured_url", return_value="http://127.0.0.1:8765/mcp"),
            mock.patch.object(mcp_client.anyio, "run", return_value="ok") as run,
        ):
            self.assertEqual(mcp_client.call_tool("status", timeout=1.25), "ok")

        run.assert_called_once_with(
            mcp_client._call_tool_async,
            "http://127.0.0.1:8765/mcp",
            "status",
            {},
            1.25,
        )


class MCPClientAsyncTest(unittest.IsolatedAsyncioTestCase):
    async def test_async_client_applies_timeout_to_http_and_sse_reads(self):
        stream_kwargs = {}

        class FakeStream:
            async def __aenter__(self):
                return "read", "write", lambda: None

            async def __aexit__(self, *_args):
                return False

        class FakeSession:
            def __init__(self, read, write):
                self.read = read
                self.write = write

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

            async def initialize(self):
                return None

            async def call_tool(self, name, kwargs):
                return SimpleNamespace(content=[SimpleNamespace(text="ok")], isError=False)

        def fake_streamablehttp_client(*_args, **kwargs):
            stream_kwargs.update(kwargs)
            return FakeStream()

        with (
            mock.patch.object(mcp_client, "streamablehttp_client", fake_streamablehttp_client),
            mock.patch.object(mcp_client, "ClientSession", FakeSession),
        ):
            result = await mcp_client._call_tool_async(
                "http://127.0.0.1:8765/mcp",
                "status",
                {},
                1.25,
            )

        self.assertEqual(result, "ok")
        self.assertEqual(stream_kwargs["timeout"], 1.25)
        self.assertEqual(stream_kwargs["sse_read_timeout"], 1.25)


if __name__ == "__main__":
    unittest.main()

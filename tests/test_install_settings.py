import unittest

from scripts import install_settings


class InstallSettingsTest(unittest.TestCase):
    def test_defaults_to_http_mcp_server(self):
        settings = install_settings.merge({}, "python3", "/remote/repo")

        self.assertEqual(settings["mcpServers"]["cc-jukebox"], {
            "type": "http",
            "url": install_settings.DEFAULT_MCP_URL,
        })
        self.assertEqual(settings["statusLine"]["command"], "python3 -m cc_jukebox statusline")

    def test_can_write_custom_http_mcp_server(self):
        settings = install_settings.merge(
            {},
            "python3",
            "/remote/repo",
            mcp_url="http://127.0.0.1:9876/mcp",
        )

        self.assertEqual(settings["mcpServers"]["cc-jukebox"], {
            "type": "http",
            "url": "http://127.0.0.1:9876/mcp",
        })


if __name__ == "__main__":
    unittest.main()

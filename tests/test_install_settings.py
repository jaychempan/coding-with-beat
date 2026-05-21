import unittest

from scripts import install_settings


class InstallSettingsTest(unittest.TestCase):
    def test_defaults_to_http_mcp_server(self):
        settings = install_settings.merge({}, "python3", "/remote/repo")

        self.assertEqual(settings["mcpServers"]["coding-with-beat"], {
            "type": "http",
            "url": install_settings.DEFAULT_MCP_URL,
        })
        self.assertEqual(settings["statusLine"]["command"], "python3 -m coding_with_beat statusline")

    def test_can_write_custom_http_mcp_server(self):
        settings = install_settings.merge(
            {},
            "python3",
            "/remote/repo",
            mcp_url="http://127.0.0.1:9876/mcp",
        )

        self.assertEqual(settings["mcpServers"]["coding-with-beat"], {
            "type": "http",
            "url": "http://127.0.0.1:9876/mcp",
        })

    def test_migrates_legacy_cc_jukebox_settings_to_coding_with_beat(self):
        settings = {
            "mcpServers": {
                "cc-jukebox": {
                    "type": "http",
                    "url": "http://127.0.0.1:8765/mcp",
                },
            },
            "statusLine": {
                "type": "command",
                "command": "python3 -m cc_jukebox statusline",
                "_owner": "cc-jukebox",
            },
            "hooks": {
                "UserPromptExpansion": [
                    {
                        "matcher": "juke",
                        "hooks": [{"type": "command", "command": "python3 -m cc_jukebox hook"}],
                        "_owner": "cc-jukebox",
                    },
                ],
            },
        }

        migrated = install_settings.merge(settings, "python3", "/repo")

        self.assertNotIn("cc-jukebox", migrated["mcpServers"])
        self.assertIn("coding-with-beat", migrated["mcpServers"])
        self.assertEqual(migrated["statusLine"]["command"], "python3 -m coding_with_beat statusline")
        self.assertEqual(migrated["statusLine"]["_owner"], "coding-with-beat")
        self.assertEqual(len(migrated["hooks"]["UserPromptExpansion"]), 1)
        self.assertEqual(migrated["hooks"]["UserPromptExpansion"][0]["matcher"], "cwb")
        self.assertEqual(migrated["hooks"]["UserPromptExpansion"][0]["_owner"], "coding-with-beat")


if __name__ == "__main__":
    unittest.main()

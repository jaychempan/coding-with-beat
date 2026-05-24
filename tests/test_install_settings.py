import unittest

from scripts import install_settings


class InstallSettingsTest(unittest.TestCase):
    def test_does_not_write_mcp_servers_to_settings(self):
        # MCP server is now registered via `claude mcp add` (writes to ~/.claude.json),
        # not settings.json. merge() must not add mcpServers here.
        settings = install_settings.merge({}, "python3", "/remote/repo")

        self.assertNotIn("mcpServers", settings)
        self.assertEqual(settings["statusLine"]["command"], "python3 -m coding_with_beat statusline")

    def test_mcp_url_param_accepted_without_writing_to_settings(self):
        # mcp_url is still accepted (used by install.sh for `claude mcp add`),
        # but must not be written into settings.json mcpServers.
        settings = install_settings.merge(
            {},
            "python3",
            "/remote/repo",
            mcp_url="http://127.0.0.1:9876/mcp",
        )

        self.assertNotIn("mcpServers", settings)

    def test_migrates_legacy_cc_jukebox_settings(self):
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

        # Legacy mcpServers entry removed; new registration is via claude mcp add
        self.assertNotIn("mcpServers", migrated)
        self.assertEqual(migrated["statusLine"]["command"], "python3 -m coding_with_beat statusline")
        self.assertEqual(migrated["statusLine"]["_owner"], "coding-with-beat")
        self.assertEqual(len(migrated["hooks"]["UserPromptExpansion"]), 1)
        self.assertEqual(migrated["hooks"]["UserPromptExpansion"][0]["matcher"], "cwb")
        self.assertEqual(migrated["hooks"]["UserPromptExpansion"][0]["_owner"], "coding-with-beat")


if __name__ == "__main__":
    unittest.main()

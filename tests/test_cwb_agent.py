import json
import unittest
from unittest import mock

from coding_with_beat import cwb_agent


class CwbAgentTest(unittest.TestCase):
    def test_parse_claude_plan_accepts_print_mode_wrapper(self):
        raw = json.dumps(
            {
                "type": "result",
                "result": json.dumps(
                    {
                        "command": "play",
                        "args": ["稻香 周杰伦"],
                        "note": "",
                    },
                    ensure_ascii=False,
                ),
            },
            ensure_ascii=False,
        )

        plan = cwb_agent.parse_claude_plan(raw)

        self.assertEqual(plan.command, "play")
        self.assertEqual(plan.args, ("稻香 周杰伦",))

    def test_normalize_plan_maps_aliases_and_validates_args(self):
        self.assertEqual(
            cwb_agent.normalize_plan({"command": "favorite", "args": []}).command,
            "like",
        )
        self.assertEqual(
            cwb_agent.normalize_plan({"command": "source", "args": ["qq music"]}).args,
            ("qq_music",),
        )
        self.assertEqual(
            cwb_agent.normalize_plan({"command": "mode", "args": ["random"]}).args,
            ("shuffle",),
        )
        with self.assertRaises(cwb_agent.CwbAgentError):
            cwb_agent.normalize_plan({"command": "status", "args": ["extra"]})

    def test_build_claude_command_uses_headless_json_planner(self):
        cmd = cwb_agent.build_claude_command("prompt")

        self.assertIn("-p", cmd)
        self.assertIn("--no-session-persistence", cmd)
        self.assertIn("--tools", cmd)
        self.assertIn("", cmd)
        self.assertIn("--max-turns", cmd)
        self.assertIn("1", cmd)
        self.assertNotIn("--json-schema", cmd)
        self.assertNotIn("--output-format", cmd)
        self.assertNotIn("--bare", cmd)

    def test_system_prompt_biases_chinese_next_to_skip_not_search(self):
        self.assertIn("播放下一首", cwb_agent._SYSTEM_PROMPT)
        self.assertIn('"command":"next"', cwb_agent._SYSTEM_PROMPT)
        self.assertIn("matches the rules below", cwb_agent._SYSTEM_PROMPT)

    def test_detect_lang_preserves_cjk_output_path(self):
        self.assertEqual(cwb_agent._detect_lang("play lofi beats"), "en")
        self.assertEqual(cwb_agent._detect_lang("播放 周杰伦"), "zh")

    def test_play_number_needs_library_add_uses_friendly_card(self):
        text = cwb_agent._format_result(
            cwb_agent.CwbPlan("play_number", ("1",)),
            1,
            'Found "孤勇者 — 陈奕迅" in the Apple Music catalog, but full playback did not start.\n'
            "Opened the Music.app search page. Add the track to your library, then try again.",
            lang="zh",
        )

        self.assertIn("孤勇者 — 陈奕迅", text)
        self.assertIn("添加到资料库", text)
        self.assertNotIn("unsupported", text)

    def test_hook_timeout_covers_child_claude_and_cli_timeouts(self):
        self.assertGreater(
            cwb_agent.HOOK_TIMEOUT,
            cwb_agent._DEFAULT_CLAUDE_TIMEOUT + cwb_agent._DEFAULT_CLI_TIMEOUT,
        )

    def test_execute_plan_invokes_local_coding_with_beat_module_without_shell(self):
        completed = mock.Mock(returncode=0, stdout="play sent\n")
        with mock.patch.object(cwb_agent.subprocess, "run", return_value=completed) as run:
            code, output = cwb_agent.execute_plan(cwb_agent.CwbPlan("play", ("稻香 周杰伦",)))

        self.assertEqual(code, 0)
        self.assertEqual(output, "play sent\n")
        self.assertEqual(run.call_args.args[0][-2:], ["play", "稻香 周杰伦"])
        self.assertIsNone(run.call_args.kwargs.get("shell"))

    def test_child_claude_disables_coding_with_beat_hooks(self):
        completed = mock.Mock(
            returncode=0,
            stdout=json.dumps({"result": json.dumps({"command": "status", "args": []})}),
        )
        with mock.patch.object(cwb_agent.subprocess, "run", return_value=completed) as run:
            plan = cwb_agent.run_child_claude("status")

        self.assertEqual(plan.command, "status")
        self.assertEqual(run.call_args.kwargs["env"]["CWB_DISABLE_HOOK"], "1")

    def test_prompt_expansion_uses_child_agent_and_blocks_main_context(self):
        event = {
            "hook_event_name": "UserPromptExpansion",
            "command_name": "cwb",
            "command_args": "来点适合 debug 的歌",
        }

        with mock.patch.object(cwb_agent, "run_intent", return_value="正在播放"):
            response = cwb_agent.handle_prompt_expansion(event)

        self.assertEqual(response["decision"], "block")
        self.assertEqual(response["reason"], f"{cwb_agent._CWB_HEADER}\n正在播放")

    def test_non_cwb_prompt_expansion_is_ignored(self):
        event = {
            "hook_event_name": "UserPromptExpansion",
            "command_name": "other",
            "command_args": "play",
        }

        self.assertIsNone(cwb_agent.handle_prompt_expansion(event))


if __name__ == "__main__":
    unittest.main()

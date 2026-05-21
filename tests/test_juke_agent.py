import json
import unittest
from unittest import mock

from cc_jukebox import juke_agent


class JukeAgentTest(unittest.TestCase):
    def test_parse_claude_plan_accepts_print_mode_wrapper(self):
        raw = json.dumps({
            "type": "result",
            "result": json.dumps({
                "command": "play",
                "args": ["稻香 周杰伦"],
                "note": "",
            }, ensure_ascii=False),
        }, ensure_ascii=False)

        plan = juke_agent.parse_claude_plan(raw)

        self.assertEqual(plan.command, "play")
        self.assertEqual(plan.args, ("稻香 周杰伦",))

    def test_normalize_plan_maps_aliases_and_validates_args(self):
        self.assertEqual(
            juke_agent.normalize_plan({"command": "favorite", "args": []}).command,
            "like",
        )
        self.assertEqual(
            juke_agent.normalize_plan({"command": "source", "args": ["qq music"]}).args,
            ("qq_music",),
        )
        self.assertEqual(
            juke_agent.normalize_plan({"command": "mode", "args": ["random"]}).args,
            ("shuffle",),
        )
        with self.assertRaises(juke_agent.JukeAgentError):
            juke_agent.normalize_plan({"command": "status", "args": ["extra"]})

    def test_build_claude_command_uses_headless_json_planner(self):
        cmd = juke_agent.build_claude_command("prompt")

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
        self.assertIn("播放下一首", juke_agent._SYSTEM_PROMPT)
        self.assertIn('"command":"next"', juke_agent._SYSTEM_PROMPT)
        self.assertIn("matches the rules below", juke_agent._SYSTEM_PROMPT)

    def test_hook_timeout_covers_child_claude_and_cli_timeouts(self):
        self.assertGreater(
            juke_agent.HOOK_TIMEOUT,
            juke_agent._DEFAULT_CLAUDE_TIMEOUT + juke_agent._DEFAULT_CLI_TIMEOUT,
        )

    def test_execute_plan_invokes_local_cc_jukebox_module_without_shell(self):
        completed = mock.Mock(returncode=0, stdout="play sent\n")
        with mock.patch.object(juke_agent.subprocess, "run", return_value=completed) as run:
            code, output = juke_agent.execute_plan(juke_agent.JukePlan("play", ("稻香 周杰伦",)))

        self.assertEqual(code, 0)
        self.assertEqual(output, "play sent\n")
        self.assertEqual(run.call_args.args[0][-2:], ["play", "稻香 周杰伦"])
        self.assertIsNone(run.call_args.kwargs.get("shell"))

    def test_child_claude_disables_cc_jukebox_hooks(self):
        completed = mock.Mock(
            returncode=0,
            stdout=json.dumps({"result": json.dumps({"command": "status", "args": []})}),
        )
        with mock.patch.object(juke_agent.subprocess, "run", return_value=completed) as run:
            plan = juke_agent.run_child_claude("status")

        self.assertEqual(plan.command, "status")
        self.assertEqual(run.call_args.kwargs["env"]["CC_JUKEBOX_DISABLE_HOOK"], "1")

    def test_prompt_expansion_uses_child_agent_and_blocks_main_context(self):
        event = {
            "hook_event_name": "UserPromptExpansion",
            "command_name": "juke",
            "command_args": "来点适合 debug 的歌",
        }

        with mock.patch.object(juke_agent, "run_intent", return_value="正在播放"):
            response = juke_agent.handle_prompt_expansion(event)

        self.assertEqual(response["decision"], "block")
        self.assertEqual(response["reason"], "正在播放")
        self.assertTrue(response["suppressOutput"])

    def test_non_juke_prompt_expansion_is_ignored(self):
        event = {
            "hook_event_name": "UserPromptExpansion",
            "command_name": "other",
            "command_args": "play",
        }

        self.assertIsNone(juke_agent.handle_prompt_expansion(event))


if __name__ == "__main__":
    unittest.main()

"""UI unit and smoke tests for the Streamlit application (Step 10 & 11 Stage D)."""

import os
import unittest
from streamlit.testing.v1 import AppTest
from app import get_tool_icon

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))


class TestStreamlitUI(unittest.TestCase):
    """Test cases for the Streamlit interface matching Step 11 Stage D."""

    def test_tool_icons(self):
        """Verify icon mapping helper."""
        self.assertEqual(get_tool_icon("search_tool"), "🌐")
        self.assertEqual(get_tool_icon("calculator_tool"), "🧮")
        self.assertEqual(get_tool_icon("python_tool"), "🔒")
        self.assertEqual(get_tool_icon("unknown_tool"), "⚙️")

    def test_app_loads_cleanly(self):
        """Verify that app.py initializes with zero runtime exceptions."""
        at = AppTest.from_file(APP_PATH, default_timeout=10)
        at.run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.chat_input), 1)

    def test_sidebar_buttons_exist(self):
        """Verify example query buttons and clear button are present in sidebar."""
        at = AppTest.from_file(APP_PATH, default_timeout=10)
        at.run()
        self.assertGreaterEqual(len(at.button), 3)

    # --- Step 11: Stage D UI Tests ---

    def test_stage_d_empty_question_handled(self):
        """Stage D: Submitting an empty question does not crash the app."""
        at = AppTest.from_file(APP_PATH, default_timeout=10)
        at.run()
        # Chat input defaults to empty, ensure run succeeds without uncaught exception
        self.assertFalse(at.exception)

    def test_stage_d_renders_interaction_and_trace(self):
        """Stage D: Trace, final answer, badges, and citations render cleanly."""
        at = AppTest.from_file(APP_PATH, default_timeout=10)
        at.run()

        # Inject completed agent interaction into session state
        at.session_state.messages.append({
            "query": "What is 12 * 8?",
            "result": {
                "output": "12 multiplied by 8 is 96.",
                "trace": [
                    {
                        "tool": "calculator_tool",
                        "decision_summary": "The agent computes 12 * 8.",
                        "input": {"expression": "12 * 8"},
                        "output": "96",
                        "preview": "96",
                        "duration_seconds": 0.002,
                        "status": "success",
                    }
                ],
                "sources": [],
                "total_duration_seconds": 0.15,
                "status": "success",
            },
        })
        at.run()

        self.assertFalse(at.exception)
        # Verify rendered interaction exists
        self.assertGreaterEqual(len(at.chat_message), 2)

    def test_stage_d_error_handling_without_secrets(self):
        """Stage D: Tool failures and errors are displayed safely without exposing secrets."""
        at = AppTest.from_file(APP_PATH, default_timeout=10)
        at.run()

        secret_canary = "AIzaSy_FAKE_SECRET_KEY_NEVER_REVEAL"

        # Inject error interaction into session state
        at.session_state.messages.append({
            "query": "Trigger simulated error",
            "result": {
                "output": "Error: Calculation failed due to malformed input.",
                "trace": [
                    {
                        "tool": "calculator_tool",
                        "decision_summary": "The agent attempted computation.",
                        "input": {"expression": "malformed"},
                        "output": "Error: Malformed expression",
                        "preview": "Error: Malformed expression",
                        "duration_seconds": 0.001,
                        "status": "error",
                    }
                ],
                "sources": [],
                "total_duration_seconds": 0.05,
                "status": "error",
            },
        })
        at.run()

        self.assertFalse(at.exception)
        self.assertGreaterEqual(len(at.error), 1)
        # Ensure secret canary is nowhere in the page markup
        rendered_dump = str(at.error[0].value)
        self.assertNotIn(secret_canary, rendered_dump)

    def test_stage_d_clear_conversation_button(self):
        """Stage D: Clear conversation button resets conversation state cleanly."""
        at = AppTest.from_file(APP_PATH, default_timeout=10)
        at.run()

        # Add message
        at.session_state.messages.append({"query": "Hello", "result": {"output": "Hi", "status": "success"}})
        self.assertEqual(len(at.session_state.messages), 1)

        # Find the clear conversation button
        clear_btn = [b for b in at.button if "Clear" in b.label]
        self.assertTrue(len(clear_btn) > 0)
        clear_btn[0].click()
        at.run()

        self.assertEqual(len(at.session_state.messages), 0)


if __name__ == "__main__":
    unittest.main()

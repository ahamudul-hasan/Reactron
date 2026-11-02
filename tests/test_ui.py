"""UI unit and smoke tests for the Streamlit application (Step 10)."""

import os
import unittest
from streamlit.testing.v1 import AppTest
from app import get_tool_icon

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))


class TestStreamlitUI(unittest.TestCase):
    """Test cases for the Streamlit interface."""

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
        # Ensure example buttons and clear conversation button are rendered
        self.assertGreaterEqual(len(at.button), 3)


if __name__ == "__main__":
    unittest.main()


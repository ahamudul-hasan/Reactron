"""Unit tests for the Python dry-run guardrail tool."""

import unittest
from tools.python_tool import python_tool, run_python_code


class TestPythonTool(unittest.TestCase):
    """Test cases for the dry-run Python tool."""

    def test_dry_run_safety_notice(self):
        """Test that calling the tool returns the disabled execution safety notice."""
        result = run_python_code("print('Hello World')")
        self.assertIn("Security Notice", result)
        self.assertIn("Python execution is disabled in this version for security", result)
        self.assertIn("Syntax Valid", result)
        self.assertIn("print('Hello World')", result)

    def test_syntax_error_detection(self):
        """Test that invalid Python syntax is flagged without crashing."""
        result = run_python_code("def broken_func(:\n    pass")
        self.assertIn("Syntax Error", result)

    def test_zero_execution_guarantee(self):
        """Verify that potentially malicious code is not executed."""
        # Attempt to set a global flag or perform unsafe operation
        test_var_name = "__REACTRON_TEST_CANARY__"
        self.assertFalse(hasattr(__builtins__, test_var_name))

        payload = f"import builtins; builtins.{test_var_name} = True"
        result = run_python_code(payload)

        # The notice should be returned, but the Canary variable must NOT exist
        self.assertIn("Security Notice", result)
        self.assertFalse(hasattr(__builtins__, test_var_name))

    def test_empty_and_whitespace_input(self):
        """Test rejection of empty or blank inputs."""
        self.assertIn("Error: Code snippet cannot be empty", run_python_code(""))
        self.assertIn("Error: Code snippet cannot be empty", run_python_code("   \n\t"))

    def test_non_string_input(self):
        """Test rejection of non-string inputs."""
        self.assertIn("Error: Code snippet must be a string", run_python_code(12345))
        self.assertIn("Error: Code snippet must be a string", run_python_code(None))

    def test_exceeding_max_length(self):
        """Test that code exceeding max length is rejected."""
        long_code = "# harmless comment\n" * 150
        self.assertIn("exceeds maximum allowed length", run_python_code(long_code))

    def test_langchain_tool_metadata_and_invocation(self):
        """Verify the LangChain @tool wrapper attributes and execution."""
        self.assertEqual(python_tool.name, "python_tool")
        self.assertTrue(len(python_tool.description) > 0)

        # Invoke through LangChain tool protocol
        res = python_tool.invoke({"code": "x = 42\ny = x * 2"})
        self.assertIn("Security Notice", res)
        self.assertIn("Syntax Valid", res)


if __name__ == "__main__":
    unittest.main()


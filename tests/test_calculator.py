"""Unit tests for the calculator tool."""

import unittest
from tools.calculator_tool import calculate, calculator_tool


class TestCalculatorTool(unittest.TestCase):
    """Test cases for the calculator tool."""

    def test_basic_multiplication(self):
        """Test basic multiplication from blueprint: 12 * 8 -> 96."""
        self.assertEqual(calculate("12 * 8"), "96")

    def test_percentage_change_expression(self):
        """Test composite arithmetic from blueprint: (150 - 120) / 120 * 100 -> 25."""
        self.assertEqual(calculate("(150 - 120) / 120 * 100"), "25")

    def test_population_percentage_expression(self):
        """Test blueprint example: 5 / 100 * 170000000 -> 8500000."""
        self.assertEqual(calculate("5 / 100 * 170000000"), "8500000")

    def test_numbers_with_comma_separators(self):
        """Test handling of thousands commas."""
        self.assertEqual(calculate("5 / 100 * 170,000,000"), "8500000")

    def test_caret_exponentiation(self):
        """Test caret conversion to exponentiation."""
        self.assertEqual(calculate("2 ^ 3"), "8")

    def test_percent_symbol_shorthand(self):
        """Test percentage sign conversion."""
        self.assertEqual(calculate("5% * 100"), "5")

    def test_floating_point_result(self):
        """Test non-integer float output."""
        self.assertEqual(calculate("1 / 4"), "0.25")

    def test_empty_and_whitespace_input(self):
        """Test rejection of empty inputs."""
        self.assertIn("Error: Expression cannot be empty", calculate(""))
        self.assertIn("Error: Expression cannot be empty", calculate("   "))

    def test_non_string_input(self):
        """Test rejection of non-string inputs."""
        self.assertIn("Error: Expression must be a string", calculate(None))
        self.assertIn("Error: Expression must be a string", calculate(123))

    def test_exceeding_max_length(self):
        """Test expression length limit."""
        long_expr = "1 + " * 60 + "1"
        self.assertIn("exceeds maximum length", calculate(long_expr))

    def test_disallowed_characters_and_injections(self):
        """Test strict rejection of letters, variables, and potential injection attacks."""
        self.assertIn("Error: Invalid characters", calculate("__import__('os').system('dir')"))
        self.assertIn("Error: Invalid characters", calculate("x + 1"))
        self.assertIn("Error: Invalid characters", calculate("eval('2+2')"))
        self.assertIn("Error: Invalid characters", calculate("sqrt(16)"))

    def test_unbalanced_parentheses(self):
        """Test rejection of unbalanced parentheses."""
        self.assertIn("Error: Unbalanced parentheses", calculate("(12 * 8"))
        self.assertIn("Error: Unbalanced parentheses", calculate("12 * 8)"))
        self.assertIn("Error: Unbalanced parentheses", calculate(")(12 * 8)("))

    def test_division_by_zero(self):
        """Test division by zero error handling."""
        self.assertEqual(calculate("10 / 0"), "Error: Division by zero.")

    def test_malformed_syntax(self):
        """Test malformed syntax error handling."""
        self.assertIn("Error: Malformed mathematical expression", calculate("12 + * 4"))

    def test_langchain_tool_invocation(self):
        """Test calling the LangChain wrapped tool."""
        res = calculator_tool.invoke({"expression": "12 * 8"})
        self.assertEqual(res, "96")


if __name__ == "__main__":
    unittest.main()

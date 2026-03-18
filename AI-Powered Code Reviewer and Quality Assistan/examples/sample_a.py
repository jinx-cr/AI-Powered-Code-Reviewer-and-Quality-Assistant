"""Sample file A — demonstrates various docstring quality levels.

Used by the AI Code Reviewer to show metrics like coverage and PEP 257 compliance.
"""


def add(x: int, y: int) -> int:
    """Return the sum of x and y.

    Args:
        x: First integer.
        y: Second integer.

    Returns:
        int: The sum of x and y.
    """
    return x + y


def subtract(x: int, y: int) -> int:
    """Return x minus y.

    Args:
        x: Minuend.
        y: Subtrahend.

    Returns:
        int: x minus y.
    """
    return x - y


def multiply(x, y):
    # Missing docstring — will be flagged by validator
    return x * y


def divide(x, y):
    if y == 0:
        raise ValueError("Cannot divide by zero")
    return x / y


class Calculator:
    """A simple calculator demonstrating class-level docstrings."""

    def __init__(self, precision: int = 2) -> None:
        """Initialise Calculator.

        Args:
            precision: Decimal places for float results.
        """
        self.precision = precision

    def compute(self, a, b, op: str):
        ops = {"+": add, "-": subtract, "*": multiply, "/": divide}
        if op not in ops:
            raise ValueError(f"Unknown operator: {op!r}")
        return round(ops[op](a, b), self.precision)

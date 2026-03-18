"""Sample file B — more complex examples with mixed docstring quality.

Demonstrates high-complexity functions and class hierarchies
for testing the AI Code Reviewer's metrics engine.
"""

from typing import Optional


def fibonacci(n: int) -> int:
    """Return the nth Fibonacci number.

    Args:
        n: Position in the Fibonacci sequence (0-indexed).

    Returns:
        int: The nth Fibonacci number.

    Raises:
        ValueError: If n is negative.
    """
    if n < 0:
        raise ValueError("n must be non-negative.")
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def is_prime(n: int) -> bool:
    """Check whether n is a prime number.

    Args:
        n: Integer to test.

    Returns:
        bool: True if n is prime, False otherwise.
    """
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(n ** 0.5) + 1, 2):
        if n % i == 0:
            return False
    return True


def parse_csv_line(line: str, delimiter: str = ",") -> list:
    # Missing docstring on purpose — flagged by validator
    return [cell.strip() for cell in line.split(delimiter)]


def flatten(nested: list) -> list:
    result = []
    for item in nested:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result


class DataProcessor:
    """Processes datasets with configurable transformation pipelines.

    Supports filtering, mapping, and aggregation operations.

    Args:
        data: Initial dataset as a list of dicts.
        strict: If True, raises on invalid records instead of skipping.
    """

    def __init__(self, data: list, strict: bool = False) -> None:
        """Initialise DataProcessor.

        Args:
            data: Initial dataset.
            strict: Whether to raise on invalid records.
        """
        self.data = data
        self.strict = strict
        self._pipeline = []

    def filter(self, key: str, value) -> "DataProcessor":
        """Filter records where record[key] == value.

        Args:
            key: Dict key to filter on.
            value: Required value for that key.

        Returns:
            DataProcessor: self, for chaining.
        """
        self._pipeline.append(("filter", key, value))
        return self

    def map(self, transform) -> "DataProcessor":
        """Apply a transformation function to each record.

        Args:
            transform: Callable that takes and returns a dict.

        Returns:
            DataProcessor: self, for chaining.
        """
        self._pipeline.append(("map", transform))
        return self

    def execute(self) -> list:
        """Execute the pipeline and return the processed records.

        Returns:
            list: Transformed dataset after all pipeline steps.
        """
        result = list(self.data)
        for step in self._pipeline:
            if step[0] == "filter":
                _, key, value = step
                result = [r for r in result if r.get(key) == value]
            elif step[0] == "map":
                _, transform = step
                processed = []
                for r in result:
                    try:
                        processed.append(transform(r))
                    except Exception:
                        if self.strict:
                            raise
                result = processed
        return result

    def summarise(self, key: str) -> dict:
        records = self.execute()
        values = [r[key] for r in records if key in r]
        if not values:
            return {"count": 0, "sum": 0, "min": None, "max": None, "avg": None}
        return {
            "count": len(values),
            "sum": sum(values),
            "min": min(values),
            "max": max(values),
            "avg": round(sum(values) / len(values), 2),
        }


class TextAnalyser:
    """Analyses text for word frequency, sentence count, and readability."""

    def __init__(self, text: str) -> None:
        """Initialise TextAnalyser with raw text.

        Args:
            text: The text string to analyse.
        """
        self.text = text

    def word_count(self) -> int:
        """Return total word count.

        Returns:
            int: Number of words in the text.
        """
        return len(self.text.split())

    def sentence_count(self) -> int:
        return sum(1 for ch in self.text if ch in ".!?")

    def top_words(self, n: int = 5) -> list:
        from collections import Counter
        words = [w.strip(".,!?;:\"'").lower() for w in self.text.split()]
        return Counter(words).most_common(n)

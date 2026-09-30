"""Sample inert python fixture for integration testing."""

def calculate_fibonacci(n: int) -> list[int]:
    """Return Fibonacci series up to n elements."""
    if n <= 0:
        return []
    series = [0, 1]
    while len(series) < n:
        series.append(series[-1] + series[-2])
    return series[:n]

"""Minimal smoke-test package for exercising scripts/gate.sh end-to-end."""


def greet(name: str) -> str:
    """Return a friendly greeting.

    Args:
        name: The name to greet.

    Returns:
        A greeting string.
    """
    return f"Hello, {name}!"

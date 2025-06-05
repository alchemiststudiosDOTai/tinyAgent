from ..decorators import tool


@tool
def g_login(username: str, password: str) -> str:
    """Simulate a login to the 'g' service."""
    return f"logged in user {username}"


# Access to decorated Tool instance
login_tool = g_login._tool


def get_tool():
    return login_tool


__all__ = ["login_tool", "get_tool"]

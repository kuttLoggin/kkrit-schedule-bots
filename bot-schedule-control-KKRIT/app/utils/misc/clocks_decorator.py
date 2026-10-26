

def set_clocks(action: str = "typing", emoji: str = "⏳"):
    def decorator(func):
        setattr(func, "clocks", {"action": action, "emoji": emoji})
        return func

    return decorator

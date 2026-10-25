"""Hook for Aya: replace the body with Celery `.delay(...)` calls.
Kept as a plain function so the tickets API never depends on Celery/Redis being up.
kind: "assigned" | "commented" | "resolved"
"""


def notify(kind: str, ticket_id: int, **extra) -> None:
    return None

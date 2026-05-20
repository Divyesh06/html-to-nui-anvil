import anvil.server
import anvil.tables as tables
from anvil.tables import app_tables
from uuid import uuid4


# ------------------------------------------------------------------ #
#  Get all tasks for the current user
# ------------------------------------------------------------------ #
@anvil.server.callable
def get_tasks():
    """Return all tasks as a list of dicts, ordered by creation."""
    user = anvil.users.get_user()
    if not user:
        return []

    rows = app_tables.tasks.search(
        tables.order_by("created", ascending=True),
        user=user,
    )
    return [
        {
            "id": row["task_id"],
            "title": row["title"],
            "done": row["done"],
        }
        for row in rows
    ]


# ------------------------------------------------------------------ #
#  Add a new task
# ------------------------------------------------------------------ #
@anvil.server.callable
def add_task(title):
    """Create a new task and return it as a dict."""
    user = anvil.users.get_user()
    if not user:
        raise anvil.server.PermissionDenied("Not logged in")

    task_id = str(uuid4())
    app_tables.tasks.add_row(
        task_id=task_id,
        user=user,
        title=title,
        done=False,
        created=anvil.server.get_datetime(),
    )
    return {"id": task_id, "title": title, "done": False}


# ------------------------------------------------------------------ #
#  Toggle a task's done state
# ------------------------------------------------------------------ #
@anvil.server.callable
def update_task(task_id, done):
    """Update the done status of a task."""
    user = anvil.users.get_user()
    if not user:
        raise anvil.server.PermissionDenied("Not logged in")

    row = app_tables.tasks.get(task_id=task_id, user=user)
    if row:
        row["done"] = done


# ------------------------------------------------------------------ #
#  Delete one or more tasks
# ------------------------------------------------------------------ #
@anvil.server.callable
def delete_tasks(task_ids):
    """Delete tasks by their IDs."""
    user = anvil.users.get_user()
    if not user:
        raise anvil.server.PermissionDenied("Not logged in")

    for task_id in task_ids:
        row = app_tables.tasks.get(task_id=task_id, user=user)
        if row:
            row.delete()

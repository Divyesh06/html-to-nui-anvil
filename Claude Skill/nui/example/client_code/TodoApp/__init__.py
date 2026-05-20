from ._anvil_designer import TodoAppTemplate
from anvil import *
import anvil.server
from .TaskItem import TaskItem


class TodoApp(TodoAppTemplate):
    def __init__(self, **properties):
        self.init_components(**properties)
        self.tasks = []
        self.filter_mode = "all"

    def form_show(self, **event_args):
        self._load_tasks()

    # ------------------------------------------------------------------ #
    #  Data
    # ------------------------------------------------------------------ #
    def _load_tasks(self):
        self.tasks = anvil.server.call("get_tasks")
        self._render()

    # ------------------------------------------------------------------ #
    #  Add Task (anvil-event-click + anvil-event-pressed_enter)
    # ------------------------------------------------------------------ #
    def add_task_click(self, **event_args):
        title = self.task_input.text.strip()
        if not title:
            return
        new_task = anvil.server.call("add_task", title)
        self.tasks.append(new_task)
        self.task_input.text = ""
        self._render()

    # ------------------------------------------------------------------ #
    #  Filter buttons (anvil-event-click)
    # ------------------------------------------------------------------ #
    def filter_all_click(self, **event_args):
        self.filter_mode = "all"
        self._update_filter_styles()
        self._render()

    def filter_active_click(self, **event_args):
        self.filter_mode = "active"
        self._update_filter_styles()
        self._render()

    def filter_done_click(self, **event_args):
        self.filter_mode = "done"
        self._update_filter_styles()
        self._render()

    def _update_filter_styles(self):
        """Toggle the 'active' modifier preset on filter buttons."""
        for mode, btn in [("all", self.filter_all_btn),
                          ("active", self.filter_active_btn),
                          ("done", self.filter_done_btn)]:
            if mode == self.filter_mode:
                btn.add_preset("active")
            else:
                btn.remove_preset("active")

    # ------------------------------------------------------------------ #
    #  Clear completed (anvil-event-click)
    # ------------------------------------------------------------------ #
    def clear_done_click(self, **event_args):
        done_ids = [t["id"] for t in self.tasks if t["done"]]
        if not done_ids:
            return
        anvil.server.call("delete_tasks", done_ids)
        self.tasks = [t for t in self.tasks if not t["done"]]
        self._render()

    # ------------------------------------------------------------------ #
    #  Callbacks from TaskItem sub-form
    # ------------------------------------------------------------------ #
    def _on_task_toggled(self, task_id, done):
        anvil.server.call("update_task", task_id, done)
        for t in self.tasks:
            if t["id"] == task_id:
                t["done"] = done
                break
        self._update_counts()

    def _on_task_deleted(self, task_id):
        anvil.server.call("delete_tasks", [task_id])
        self.tasks = [t for t in self.tasks if t["id"] != task_id]
        self._render()

    # ------------------------------------------------------------------ #
    #  Render
    # ------------------------------------------------------------------ #
    def _render(self):
        self.task_list.clear()

        if self.filter_mode == "active":
            visible = [t for t in self.tasks if not t["done"]]
        elif self.filter_mode == "done":
            visible = [t for t in self.tasks if t["done"]]
        else:
            visible = self.tasks

        self.empty_state.visible = len(visible) == 0

        for task in visible:
            item = TaskItem(
                task=task,
                on_toggle=self._on_task_toggled,
                on_delete=self._on_task_deleted,
            )
            self.task_list.add_component(item)

        self._update_counts()

    def _update_counts(self):
        total = len(self.tasks)
        done = sum(1 for t in self.tasks if t["done"])
        active = total - done

        self.total_count_label.text = f"{total} task{'s' if total != 1 else ''}"
        self.done_count_label.text = f"{done} completed"
        self.active_count.text = str(active)
        self.done_count.text = str(done)

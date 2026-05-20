from ._anvil_designer import TaskItemTemplate
from anvil import *


class TaskItem(TaskItemTemplate):
    def __init__(self, task=None, on_toggle=None, on_delete=None, **properties):
        self.init_components(**properties)
        self.task = task or {}
        self._on_toggle = on_toggle
        self._on_delete = on_delete

        if self.task:
            self._populate()

    def _populate(self):
        self.title_label.text = self.task.get("title", "")
        if self.task.get("done", False):
            self.checkbox.add_preset("checked")
            self.checkbox.text = "\u2713"
            self.title_label.add_preset("done")

    # ------------------------------------------------------------------ #
    #  Events (anvil-event-click in design.html)
    # ------------------------------------------------------------------ #
    def toggle_click(self, **event_args):
        self.task["done"] = not self.task.get("done", False)
        self.checkbox.toggle_preset("checked")
        self.checkbox.text = "\u2713" if self.task["done"] else ""
        self.title_label.toggle_preset("done")
        if self._on_toggle:
            self._on_toggle(self.task["id"], self.task["done"])

    def delete_click(self, **event_args):
        if self._on_delete:
            self._on_delete(self.task["id"])

---
name: nui
description: Build UI for Anvil applications using NUI — a framework that lets you write layouts in HTML and convert them to valid Anvil Forms. Use this skill whenever the user wants to create, edit, or convert an Anvil UI using NUI, design.html files, html_to_nui.py, form_template.yaml, or any NUI component. Also trigger when the user asks about NUI attributes (anvil-var, anvil-event-*, anvil-is-container), component mapping, dynamic form embedding, or managing CSS classes in NUI Python code.
---

# NUI Skill

NUI lets you write Anvil UI in HTML, then convert it to a valid `form_template.yaml`. All logic stays in Python; no JavaScript is allowed.

## Workflow

1. Write `design.html` inside the form folder
2. Run the converter: `python html_to_nui.py /path/to/design.html`
3. This generates `form_template.yaml` — ready for Anvil
4. Write all UI logic in `__init__.py` (Python only)

---

## Special NUI Attributes

These attributes are **removed automatically** during conversion. They are instructions to the converter, not final component properties.

| Attribute | Purpose |
|---|---|
| `anvil-var="name"` | Exposes component as `self.name` in Python |
| `anvil-event-click="handler"` | Binds click → `def handler(self, **event_args)` |
| `anvil-event-<event>="handler"` | Any supported event (see Events table) |
| `anvil-is-container` | Forces element to become a Container even if empty |

### Example HTML

```html
<div anvil-var="card_wrapper" anvil-is-container>
  <button
    anvil-var="save_btn"
    anvil-event-click="save_clicked">
    Save
  </button>
  <input anvil-var="email_input" placeholder="Email" />
</div>
```

### Resulting Python access

```python
self.card_wrapper          # Container
self.save_btn              # Button
self.email_input.text      # TextBox value

def save_clicked(self, **event_args):
    print(self.email_input.text)
```

---

## Component Mapping

| HTML Tag | NUI Component |
|---|---|
| `label`, `p`, `span`, `h1`–`h6` | Label |
| `button` | Button |
| `textarea` | TextArea |
| `input` | TextBox |
| `a` | Link |
| `img` | Image |
| Any element with children | Container |
| `anvil-is-container` present | Container (forced) |
| Unknown fallback | Label |

---

## Component Properties

Virtually every component supports flexible properties.

| Property          | Type          | Description           |
| ----------------- | ------------- | --------------------- |
| `html_tag`        | string        | Original HTML tag     |
| `preset`          | list          | CSS classes           |
| `text`            | string        | Displayed text        |
| `text_type`       | string        | `"text"` or `"html"`  |
| `text_align`      | string        | Alignment             |
| `font_size`       | string/number | Font size             |
| `font`            | string        | Font family           |
| `font_weight`     | string        | Font weight           |
| `foreground`      | string        | Text color            |
| `background`      | string        | Background color      |
| `width`           | string/number | Width                 |
| `height`          | string/number | Height                |
| `visible`         | boolean       | Show/hide             |
| `enabled`         | boolean       | Enable/disable        |
| `border_radius`   | string/number | Corner rounding       |
| `border_size`     | string        | Border thickness      |
| `border_style`    | string        | Border style          |
| `border_color`    | string        | Border color          |
| `margin`          | string        | Outer spacing         |
| `padding`         | string        | Inner spacing         |
| `icon`            | string        | Icon name             |
| `icon_align`      | string        | Icon alignment        |
| `icon_size`       | string        | Icon size             |
| `css`             | string        | Custom CSS            |
| `hover_css`       | string        | Hover CSS             |
| `active_css`      | string        | Active CSS            |
| `disabled_css`    | string        | Disabled CSS          |
| `focus_css`       | string        | Focus CSS             |
| `placeholder_css` | string        | Placeholder style     |
| `attributes`      | dict          | Extra HTML attributes |
| `type`            | string        | Input type            |
| `placeholder`     | string        | Placeholder text      |

---

## Binding Events from Python — the `@handle` decorator

NUI does **not** auto-wire event handlers by method name. Defining `def form_show(self, **event_args):` alone is a no-op — the method will never be called. To bind any event from Python, decorate the method with `@handle` (Anvil imports by default):

```python

class MyForm(MyFormTemplate):
    def __init__(self, **properties):
        self.init_components(**properties)

    @handle("", "show")              # the form itself, "show" event
    def form_show(self, **event_args):
        ...

    @handle("save_btn", "click")     # a named component, "click" event
    def save_clicked(self, **event_args):
        ...
```

- **First argument** — a component selector. `""` (empty string) means the form itself. Otherwise it's the `anvil-var` name of a child component.
- **Second argument** — the event name (`"show"`, `"hide"`, `"click"`, `"input"`, `"change"`, `"pressed_enter"`, `"focus"`, `"lost_focus"`, `"hover"`, `"hover_out"`, …).
- `show` / `hide` are **general component events** — they fire on every NUI component (and on the form, which is also a component) when it's added to or removed from the DOM. The "form load" pattern is just `@handle("", "show")` on the form.

`@handle` and the HTML `anvil-event-*` directive are equivalent — pick whichever is cleaner. Without one of them, the handler is silently never called.

---

## Events

| Event           | Applies To              |
| --------------- | ----------------------- |
| `click`         | Button, Container, Link |
| `input`         | Inputs                  |
| `change`        | Inputs                  |
| `pressed_enter` | TextBox                 |
| `focus`         | Inputs                  |
| `lost_focus`    | Inputs                  |
| `hover`         | Interactive components  |
| `hover_out`     | Interactive components  |
| `show`          | All components (incl. forms) — fires when added to the DOM |
| `hide`          | All components (incl. forms) — fires when removed from the DOM |

Example:

```python

def label_1_click(self, **event_args):
    print(event_args['sender']) #The sender of the event
    print(event_args['event']) #JS event info
```

Bind declaratively with `anvil-event-<event>="handler_name"` in HTML. Only bind manually in Python for dynamically created components.

For additional js events, you can declare them in code

```python
self.label_1.add_event("my_js_event", self.label_1_click)
```

---

## DOM Access

Every component exposes its raw DOM element for properties not covered by NUI:

```python
self.my_component.dom  # Raw DOM element
```

---

## Theme Colors — `theme/parameters.yaml`

App-wide named colors live in `theme/parameters.yaml` under `color_scheme.colors`. The reference syntax **differs depending on where the CSS lives** — they are not interchangeable:

| CSS location | Syntax | Spaces in name |
|---|---|---|
| `design.html` `<style>` block (form-level) | `theme:Primary_500` | replaced with `_` |
| `theme/assets/theme.css` (global) | `%color:Primary 500%` | **kept as-is** |

```yaml
# theme/parameters.yaml
color_scheme:
  colors:
  - {color: '#ffffff',             name: White}
  - {color: '#393567',             name: Primary 500}
  - {color: '#3b82f6',             name: Accent Blue}
  - {color: 'rgba(0, 0, 0, 0.6)',  name: Overlay Dim}
  - {color: 'hsl(160, 84%, 39%)',  name: Success Mint}
  - {color: 'tomato',              name: Brand Pop}
```

```css
/* form-level — inside design.html <style> */
.btn-primary {
  background: theme:Primary_500;
  color:      theme:White;
}
.modal-scrim { background: theme:Overlay_Dim; }
```

```css
/* global — theme/assets/theme.css */
.btn-primary {
  background: %color:Primary 500%;
  color:      %color:White%;
}
.modal-scrim { background: %color:Overlay Dim%; }
```

**Adding colors.** You can extend `parameters.yaml` whenever you need a new token. Any CSS color value works in the `color:` field — hex, `rgb(...)`, `rgba(...)`, `hsl(...)`, or named colors (see the YAML above for one of each).

**When to use a token vs. a raw value.**

- Brand / semantic colors that should be consistent app-wide (primary, secondary, error, surface, text) → add to `parameters.yaml` and reference via the appropriate syntax for that file.
- One-off colors local to a single component's `<style>` block → raw values are fine.

---

## Shared CSS — `theme/assets/theme.css`

CSS classes that are reused across multiple forms (buttons, chips, panels, layout primitives, brand colors, anything design-system-y) belong in **`theme/assets/theme.css`**, not duplicated inside each form's `<style>` block.

Anvil loads `theme.css` globally for every form. NUI's `preset` is just a list of class names on the rendered DOM element — so any class defined in `theme.css` can be used as a preset on any NUI component without ever appearing in that form's `design.html` `<style>` block.

```css
/* theme/assets/theme.css */
.btn-primary {
  background: #3b82f6;
  color: white;
  border-radius: 8px;
  padding: 10px 16px;
  font-weight: 600;
}
.btn-primary:hover { background: #2563eb; }

.chip-success { background: #d1fae5; color: #047857; }
.chip-danger  { background: #fee2e2; color: #b91c1c; }
```

```html
<!-- any form's design.html -->
<button class="btn-primary">Save</button>
<span class="chip chip-success">Resolved</span>
```

```python
# can be toggled from Python like any preset
self.status_chip.add_preset("chip-danger")
self.status_chip.remove_preset("chip-success")
```

**When to put a class in `theme.css` vs the form's `<style>` block:**

- Used by 2+ forms → `theme.css`.
- Visual primitives that should look identical app-wide (buttons, chips, cards, badges, headings, color tokens) → `theme.css`.
- Layout that's specific to one form (this dashboard's grid, that modal's column widths) → that form's `<style>` block.

> Some skill setups don't have `theme/assets/theme.css` yet — create the file if it's missing; Anvil will pick it up automatically.

---

## Managing CSS Classes in Python

```python
self.my_component.add_preset("active")
self.my_component.remove_preset("active")
self.my_component.toggle_preset("active")
```

---

## Creating Components Dynamically in Python

```python
from NUI import components as NUI

btn = NUI.Button(text="Click Me")
self.content_panel.add_component(btn)
```

---

## Embedding Other Forms

Import and mount other forms dynamically for modular UIs:

```python
from ..UserProfile import UserProfile

def show_profile(self):
    profile = UserProfile()
    self.content_container.clear()
    self.content_container.add_component(profile)
```

> **Rule**: Whenever a component needs to be reused or have multiple instances, create a dedicated form for it and add it to a container dynamically.

---

## Best Practices

- ✅ Keep all logic in Python — no JavaScript in `design.html`
- ✅ Use `anvil-var` only when you need Python access to the component
- ✅ Use `anvil-event-*` for declarative event binding
- ✅ Use `anvil-is-container` on elements that will receive dynamic children
- ✅ Create separate forms for reusable components
- ✅ Use `<style>` blocks in `design.html` only for layout-specific CSS; put any class reused across forms in `theme/assets/theme.css` and reference it as a preset
- ✅ Use `theme:Color_Name` for brand / semantic colors (defined in `theme/parameters.yaml`); reserve raw hex for one-off values local to a single form
- ✅ Bind every Python-side handler not added as an attribute using `anvil-event-*` with `@handle(selector, event)` — including form-level `@handle("", "show")`; without it the method is silently never called
- ❌ Do not write `<script>` tags in `design.html`

---

## Reference Files

- `example_app/` — Working example app; read this first if present in the skill directory
- `html_to_nui.py` — The converter script; read this if conversion behavior is unclear or unexpected

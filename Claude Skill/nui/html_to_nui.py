"""
NUI HTML → form_template.yaml converter.

"""

import os
import re
import sys

import yaml
from bs4 import BeautifulSoup, Comment, NavigableString, Tag


# --------------------------------------------------------------------------- #
#  HTML attribute → NUI component property hoisting
#  (parallels ATTR_TO_SUPER in Client_HTML_Parser.py)
# --------------------------------------------------------------------------- #

ATTR_TO_SUPER = {
    "placeholder": "placeholder",
    "type": "type",
    "value": "text",
    "disabled": "enabled",   # special-case: any value becomes False
    "src": "source",
    "alt": "alt",
    "href": "href",
    "target": "target",
}

NUI_TAG_MAPPINGS = {
    "button": "Button",
    "input": "TextBox",
    "textarea": "TextArea",
    "a": "Link",
    "img": "Image",
}


# --------------------------------------------------------------------------- #
#  CSS block extraction (selector → preset map, bare selectors → stylesheet)
# --------------------------------------------------------------------------- #

def extract_css_blocks(css_content):
    css_content = re.sub(r"/\*.*?\*/", "", css_content, flags=re.DOTALL)
    blocks, stack, current = [], [], ""
    for c in css_content:
        current += c
        if c == "{":
            stack.append("{")
        elif c == "}":
            if stack:
                stack.pop()
            if not stack:
                blocks.append(current.strip())
                current = ""
    if current.strip():
        blocks.append(current.strip())
    return blocks


def process_css_block(block, preset_map, stylesheet, parent_at_rule=None):
    block = block.strip()
    if not block:
        return

    if block.startswith("@"):
        brace_index = block.find("{")
        if brace_index == -1:
            stylesheet.append(block)
            return
        at_rule_header = block[:brace_index + 1].strip() + "\n"
        inner_content = block[brace_index + 1:-1].strip()
        for inner in extract_css_blocks(inner_content):
            process_css_block(inner, preset_map, stylesheet,
                              parent_at_rule=at_rule_header)
        return

    m = re.match(r"([^{]+)\s*{(.*)}$", block, flags=re.DOTALL)
    if not m:
        if parent_at_rule:
            stylesheet.append(f"{parent_at_rule}{block}\n}}")
        else:
            stylesheet.append(block)
        return

    selectors = m.group(1).strip().split(",")
    css_rules = m.group(2).strip()
    for sel in selectors:
        sel = sel.strip()
        if sel.startswith("."):
            parts = sel[1:].split(":", 1)
            name = parts[0]
            pseudo = f":{parts[1]}" if len(parts) > 1 else ""
            rule_text = f"{pseudo}\n{css_rules}" if pseudo else css_rules
            if parent_at_rule:
                rule_text = f"{parent_at_rule}{rule_text}\n}}"
            existing = preset_map.get(name, "")
            preset_map[name] = (existing + "\n" + rule_text).strip()
        else:
            if parent_at_rule:
                stylesheet.append(f"{parent_at_rule}{sel} {{ {css_rules} }}")
            else:
                stylesheet.append(f"{sel} {{ {css_rules} }}")


# --------------------------------------------------------------------------- #
#  HTML parsing — mirrors parse_html_element in Client_HTML_Parser.py
# --------------------------------------------------------------------------- #

def _stringify_attr_value(v):
    if isinstance(v, list):
        return " ".join(str(x) for x in v)
    return str(v)


def parse_html_element(el, standalone=False):
    """Parse a bs4 node into a plain dict, matching the runtime parser."""

    # ----- Comments / other non-Tag/non-NavigableString → drop ----- #
    if isinstance(el, Comment):
        return None

    # ----- Text nodes ----- #
    if isinstance(el, NavigableString):
        text = str(el).strip()
        if not text:
            return None
        if standalone:
            # Only child of its parent → folded into parent's `text`
            return {"text": text}
        # Sibling text → becomes a span Label
        return {"html_tag": "span", "text": text, "children": []}

    if not isinstance(el, Tag):
        return None

    tag_name = el.name.lower()
    if tag_name in ("script", "style"):
        return None

    # ----- Attributes ----- #
    mapped = {}
    raw_attrs = []
    explicit_name = None
    force_container = False
    event_bindings = {}

    for k, raw_v in el.attrs.items():
        v = _stringify_attr_value(raw_v)

        # Converter-time directives — consumed, never emitted on the component.
        if k == "anvil-var":
            explicit_name = v.strip()
            continue
        if k == "anvil-is-container":
            force_container = True
            continue
        if k.startswith("anvil-event-"):
            event_bindings[k[len("anvil-event-"):]] = v
            continue

        if k in ATTR_TO_SUPER:
            if k == "disabled":
                mapped[ATTR_TO_SUPER[k]] = False
            else:
                mapped[ATTR_TO_SUPER[k]] = v
        elif k in ("style", "class"):
            continue
        else:
            raw_attrs.append(f"{k}: {v}")

    classes = el.get("class") or []
    if isinstance(classes, str):
        classes = classes.split()

    node = {
        "html_tag": tag_name,
        "css": el.get("style") or "",
        "preset": [str(c) for c in classes],
        "attributes": raw_attrs,
        "text": "",
        "children": [],
        "_explicit_name": explicit_name,
        "_force_container": force_container,
        "_event_bindings": event_bindings,
    }
    node.update(mapped)

    # ----- Recurse into children ----- #
    child_nodes = list(el.children)
    single = len(child_nodes) == 1

    for child in child_nodes:
        parsed = parse_html_element(child, standalone=single)
        if parsed is None:
            continue
        if "text" in parsed and len(parsed) == 1:
            node["text"] += parsed["text"]
        else:
            node["children"].append(parsed)

    node["text"] = node["text"].strip()
    return node


def parse_html(html):
    soup = BeautifulSoup(html, "html.parser")

    preset_map = {}
    stylesheet = []
    for s in soup.find_all("style"):
        css = s.string or s.text or ""
        for block in extract_css_blocks(css):
            process_css_block(block, preset_map, stylesheet)

    presets = [{"name": str(n), "css": str(c)} for n, c in preset_map.items()]

    body = soup.body or soup
    components = []
    for child in body.children:
        parsed = parse_html_element(child)
        if parsed:
            components.append(parsed)

    return presets, stylesheet, components


# --------------------------------------------------------------------------- #
#  YAML building — mirrors recursively_build_components + add_component_dict
# --------------------------------------------------------------------------- #

class YAMLBuilder:

    INTERNAL_KEYS = ("children", "_explicit_name", "_force_container", "_event_bindings")

    def __init__(self):
        self.name_counts = {}

    def _auto_name(self, classname, tag):
        cls = classname.lower()
        key = f"{cls}_{tag}" if cls != tag else tag
        self.name_counts[key] = self.name_counts.get(key, 0) + 1
        return f"{key}_{self.name_counts[key]}"

    def build(self, comp):
        explicit_name = comp.get("_explicit_name")
        force_container = bool(comp.get("_force_container"))
        event_bindings = comp.get("_event_bindings") or {}

        children = comp.get("children") or []
        if force_container or children:
            classname = "Container"
        else:
            classname = NUI_TAG_MAPPINGS.get(comp["html_tag"], "Label")

        name = explicit_name or self._auto_name(classname, comp["html_tag"])

        properties = {k: v for k, v in comp.items() if k not in self.INTERNAL_KEYS}
        if classname == "Container":
            properties["true_html_structure"] = True

        node = {
            "layout_properties": {"slot": "default"},
            "name": name,
            "properties": properties,
            "type": f"form:%%nui_dep_id%%:{classname}",
        }

        if event_bindings:
            node["event_bindings"] = dict(event_bindings)

        if children:
            node["components"] = [self.build(c) for c in children]

        return node


# --------------------------------------------------------------------------- #
#  YAML safety
# --------------------------------------------------------------------------- #

def make_yaml_safe(obj):
    if isinstance(obj, dict):
        return {str(k): make_yaml_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [make_yaml_safe(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


# --------------------------------------------------------------------------- #
#  Top-level form structure
# --------------------------------------------------------------------------- #

def build_form_yaml(html):
    presets, stylesheets, components = parse_html(html)
    builder = YAMLBuilder()

    base = {
        "layout_properties": {"slot": "default"},
        "name": "Base",
        "properties": {"true_html_structure": True},
        "type": "form:%%nui_dep_id%%:Container",
        "components": [],
    }
    for comp in components:
        base["components"].append(builder.build(comp))

    # PresetsContainer (Presets + StyleSheets) — appended to Base.components,
    # matching the reference `recursively_build_components` flow.
    if presets or stylesheets:
        preset_container = {
            "layout_properties": {"slot": "default"},
            "name": "presets_container_1",
            "properties": {},
            "type": "form:%%nui_dep_id%%:PresetsContainer",
            "components": [],
        }
        for p in presets:
            preset_container["components"].append({
                "layout_properties": {"slot": "default"},
                "name": f"preset_{p['name']}",
                "properties": {
                    "name": p["name"],
                    "css": p["css"],
                    "item": p,
                },
                "type": "form:%%nui_dep_id%%:Preset",
            })
        for i, s in enumerate(stylesheets, start=1):
            preset_container["components"].append({
                "layout_properties": {"slot": "default"},
                "name": f"stylesheet_{i}",
                "properties": {"css": s, "item": {"css": s}},
                "type": "form:%%nui_dep_id%%:StyleSheet",
            })
        base["components"].append(preset_container)

    preview_settings = {
        "layout_properties": {"slot": "default"},
        "name": "preview_settings",
        "properties": {},
        "type": "form:%%nui_dep_id%%:PreviewSettings",
    }

    base_form = {
        "container": {"type": "HtmlTemplate"},
        "is_package": True,
        "components": [base, preview_settings],
    }

    return yaml.safe_dump(
        make_yaml_safe(base_form),
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )


# --------------------------------------------------------------------------- #
#  Dependency resolution + CLI entry point
# --------------------------------------------------------------------------- #

def find_nui_dep_id(start_dir):
    current = os.path.abspath(start_dir)
    while True:
        anvil_yaml_path = os.path.join(current, "anvil.yaml")
        if os.path.exists(anvil_yaml_path):
            with open(anvil_yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            for dep in data.get("dependencies", []) or []:
                if dep.get("resolution_hints", {}).get("package_name") == "NUI":
                    return dep.get("dep_id")
            return None
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def main():
    if len(sys.argv) != 2:
        print("Usage: python html_to_nui.py path/to/design.html")
        sys.exit(1)

    html_path = sys.argv[1]
    if not os.path.exists(html_path):
        print(f"File not found: {html_path}")
        sys.exit(1)

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    yaml_output = build_form_yaml(html)

    nui_dep_id = find_nui_dep_id(os.path.dirname(html_path) or ".")
    if not nui_dep_id:
        raise ValueError("NUI dependency not found in anvil.yaml")
    yaml_output = yaml_output.replace("%%nui_dep_id%%", nui_dep_id)

    output_path = os.path.join(
        os.path.dirname(html_path),
        "form_template.yaml",
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(yaml_output)
    print(f"Generated: {output_path}")


if __name__ == "__main__":
    main()

"""
Rich tree rendering for the state operation tree.

Colour scheme:
  green  — ENABLED
  red    — DISABLED
  grey46 — PARENT_DISABLED (node is internally on but parent group is off,
           or the underlying DAL is resource-disabled in the session)
"""

from confmodel_dal import component_disabled
from rich.tree import Tree

from runconf_ui.state_tree import Group, Node, State, compute_state


_COLOURS: dict[State, str] = {
    State.ENABLED:         "green",
    State.DISABLED:        "red",
    State.PARENT_DISABLED: "grey46",
}


def _format_label(label: str, state: State) -> str:
    colour = _COLOURS[state]
    return f"[bold {colour}]{label}[/]   [dim {colour}]{state.name.lower()}[/]"


# ── Node-based trees ─────────────────────────────────────────────────────────

def _render_node_branch(branch, node: Node, parent: Group | None) -> None:
    if not isinstance(node, Group):
        return
    for child, _, _ in node:
        if child.label:
            state = compute_state(child, parent=node)
            sub = branch.add(_format_label(child.label, state))
            _render_node_branch(sub, child, parent=node)
        else:
            _render_node_branch(branch, child, parent=node)


def draw_node_tree(label: str, root: Node) -> Tree:
    """Build and return a Rich Tree representing the full state hierarchy rooted at *root*."""
    root_state = compute_state(root, parent=None)
    tree = Tree(_format_label(label or root.label or "<root>", root_state))
    _render_node_branch(tree, root, parent=None)
    return tree


# ── Configuration-based trees ─────────────────────────────────────────────────

class ConfigTreeRenderer:
    def __init__(self, config, session, classes_to_draw: list[str]) -> None:
        self.config = config
        self.session = session
        self.classes_to_draw = classes_to_draw

    def draw_config_tree(self) -> Tree:
        tree = Tree(f"[bold green]{self.session.id}")
        self._render_config_branch(tree, self.session, State.ENABLED)
        return tree

    def _calc_config_state(self, dal, parent_state: State) -> State:
        if parent_state is not State.ENABLED:
            return State.PARENT_DISABLED

        if "Resource" not in self.config.superclasses(dal.className(), all=True):
            return parent_state

        if component_disabled(self.config._obj, self.session.id, dal.id):
            return State.DISABLED

        return State.ENABLED

    def _render_config_branch(self, branch, dal, parent_state: State) -> None:
        for rel, r_prop in self.config.relations(dal.className()).items():
            rel_type = r_prop["type"]

            draw = (
                rel_type in self.classes_to_draw
                or any(
                    rel_type in self.config.superclasses(c, all=True)
                    for c in self.classes_to_draw
                )
            )

            rel_vals = getattr(dal, rel)
            if not rel_vals:
                continue
            if not isinstance(rel_vals, list):
                rel_vals = [rel_vals]

            if draw:
                branch = branch.add(f"[cyan]{rel}")

            for r in rel_vals:
                r_state = self._calc_config_state(r, parent_state)
                branch_to_add = branch.add(_format_label(repr(r), r_state)) if draw else branch
                self._render_config_branch(branch_to_add, r, r_state)
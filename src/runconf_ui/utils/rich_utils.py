"""
Rich tree rendering for the state operation tree.

Colour scheme:
  green  — ENABLED
  red    — DISABLED
  grey46 — PARENT_DISABLED (node is internally on but parent group is off,
           or the underlying DAL is resource-disabled in the session)
"""

from rich.tree import Tree

from runconf_ui.state_tree import State, compute_state, Group, Node

_COLOURS: dict[State, str] = {
    State.ENABLED:         "green",
    State.DISABLED:        "red",
    State.PARENT_DISABLED: "grey46",
}


def _format_label(label: str, state: State) -> str:
    colour = _COLOURS[state]
    return f"[bold {colour}]{label}[/]   [dim {colour}]{state.name.lower()}[/]"


def _render(branch, node: Node, parent: Group | None) -> None:
    if not isinstance(node, Group):
        return
    for child, _, _ in node:
        state = compute_state(child, parent=node)
        label = child.label or "<anonymous>"
        sub   = branch.add(_format_label(label, state))
        _render(sub, child, parent=node)


def draw_tree(label: str, root: Node) -> Tree:
    """
    Build and return a Rich Tree representing the full state hierarchy
    rooted at root.
    """
    root_state = compute_state(root, parent=None)
    tree = Tree(_format_label(label or root.label or "<root>", root_state))
    _render(tree, root, parent=None)
    return tree
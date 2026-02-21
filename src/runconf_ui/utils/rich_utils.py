
from rich.tree import Tree

from runconf_ui import state_operations

_COLOUR_SCHEME = {
    "enabled": {
        "label": "[bold green]",
        "state": "[dim blue]",
    },
    "disabled": {
        "label": "[bold grey36]",
        "state": "[dim grey36]",
    },
    "generic": {
        "label": "[bold black]",
        "state": "[dim black]",
    },
}


def _get_colour_scheme_and_label(
    state: state_operations.StateOperation,
) -> tuple[str, str]:
    """Determine the colour scheme and display label for a given state operation."""
    if isinstance(state, state_operations.DisableOperation):
        colour_scheme = "enabled" if state.get_state() else "disabled"
        return colour_scheme, colour_scheme

    if isinstance(state, state_operations.AdjustableAttribute):
        colour_scheme = "enabled" if state.dal_enabled() else "disabled"
        return colour_scheme, str((state.get_state(), colour_scheme))

    return "generic", str(state.get_state())


def make_tree_label(state: state_operations.StateOperation) -> str:
    """Generate a Rich-formatted label string for a state operation."""
    colour_scheme, label_str = _get_colour_scheme_and_label(state)
    colours = _COLOUR_SCHEME[colour_scheme]
    return f"{colours['label']}{state.label}[/]   {colours['state']}{label_str}"


def add_to_tree(tree, state: state_operations.StateOperation) -> None:
    """Add a state operation node (and any children) to the given tree."""
    branch = tree.add(make_tree_label(state), state.get_state())
    if isinstance(state, state_operations.StateOperationContainer):
        for child in state.state_operations:
            add_to_tree(branch, child)


def draw_state_operation_tree(
    group_name: str,
    state_container: list[state_operations.StateOperationContainer],
) -> Tree:
    """Build and return a Rich Tree representing the state operation hierarchy."""
    tree = Tree(group_name)
    for state in state_container:
        add_to_tree(tree, state)
    return tree

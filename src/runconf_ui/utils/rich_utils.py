"""
Builds the runconf-ui trees as plain ``DrawItem`` data and renders them with Rich.

Building needs the live state tree / conffwk configuration (backend side);
rendering lives in ``runconf_ui.utils.rendering`` so a remote frontend can draw
the same trees from data it received over gRPC.
"""

from confmodel_dal import entity_excluded
from rich.tree import Tree

from runconf_ui.state_tree import Group, Node, NodeStatus, State, compute_state

# Yeah sorry about this
from runconf_ui.system_configuration.config_reader import _natural_key
from runconf_ui.utils.rendering import (
    DrawItem,
    add_items,
    format_state_label,
    render_config_tree,
    render_node_tree,
)

# Kept for backwards compatibility
_format_label = format_state_label


def sort_children(children: list[Node]) -> list[Node]:
    """Sort a list of nodes first by type (Group before Node) then by label.

    :param children: List of child nodes to sort
    :returns: Sorted list of child nodes
    :rtype: list[Node]
    """
    return sorted(
        children,
        key=lambda n: (0 if isinstance(n, Group) else 1, _natural_key(n.label or "")),
    )


# ── Node-based trees ─────────────────────────────────────────────────────────


def _node_children(node: Node) -> list[DrawItem]:
    """Labelled descendants of ``node`` as DrawItems. Unlabelled groups are
    flattened into their parent. Each item's state is computed against its
    direct parent only, and ``source`` is its NodeStatus.

    :param node: The node whose children to build
    :returns: List of DrawItems for the visible children
    """
    if not isinstance(node, Group):
        return []

    items: list[DrawItem] = []
    for child in sort_children(node.children):
        if child.label:
            state = compute_state(child, parent=node)
            items.append(
                DrawItem(
                    label=child.label,
                    state=state,
                    children=_node_children(child),
                    source=NodeStatus(child, state, node),
                )
            )
        else:
            items.extend(_node_children(child))
    return items


def node_tree_items(label: str, root: Node) -> DrawItem:
    """Build the DrawItem tree for one system.

    :param label: Label for the root node (falls back to the root's own label)
    :param root: The root node to build from
    :returns: Root DrawItem with nested children
    """
    root_state = compute_state(root, parent=None)
    return DrawItem(
        label=label or root.label or "<root>",
        state=root_state,
        children=_node_children(root),
        source=NodeStatus(root, root_state, None),
    )


def draw_node_tree(label: str, root: Node) -> Tree:
    """Build and return a Rich Tree representing the full state hierarchy.

    :param label: Label for the root node
    :param root: The root node to render from
    :returns: Rich Tree object with state hierarchy
    :rtype: Tree
    """
    return render_node_tree(node_tree_items(label, root))


# ── Configuration-based trees ─────────────────────────────────────────────────


class ConfigTreeRenderer:
    """Builds (and renders) the DAL configuration hierarchy as a tree.

    Displays the configuration object structure with state information,
    filtering to show only specified DAL classes.
    """

    def __init__(self, config, session, classes_to_draw: list[str]) -> None:
        """Initialize ConfigTreeRenderer.

        :param config: The Configuration object
        :param session: The session DAL to render from
        :param classes_to_draw: List of DAL class names to include in rendering
        """
        self.config = config
        self.session = session
        self.classes_to_draw = classes_to_draw

    def config_tree_items(self) -> list[DrawItem]:
        """Entries below the session root, as DrawItems.

        Relationship entries have ``state=None``; object entries carry their state.
        """
        return self._config_items(self.session, State.INCLUDED)

    def draw_config_tree(self) -> Tree:
        """Draw the configuration tree starting from the session.

        :returns: Rich Tree object representing the configuration
        :rtype: Tree
        """
        return render_config_tree(self.session.id, self.config_tree_items())

    def _calc_config_state(self, dal, parent_state: State) -> State:
        """Calculate the state of a DAL object based on parent and ExcludableEntity state.

        :param dal: The DAL object to calculate state for
        :param parent_state: The parent's state
        :returns: The calculated state for the DAL
        :rtype: State
        """
        if parent_state is not State.INCLUDED:
            return State.PARENT_EXCLUDED

        if "ExcludableEntity" not in self.config.superclasses(
            dal.className(), all=True
        ):
            return parent_state

        if entity_excluded(self.config._obj, self.session.id, dal.id):
            return State.EXCLUDED

        return State.INCLUDED

    def _config_items(self, dal, parent_state: State) -> list[DrawItem]:
        """Build the entries below ``dal``.

        NOTE: once a drawn relationship has been added, later relationships of the
        same object nest *under* it (this mirrors the original Rich renderer, which
        reassigned ``branch`` inside the loop).

        :param dal: The DAL object to build from
        :param parent_state: The parent's state for context
        :returns: List of DrawItems below ``dal``
        """
        top: list[DrawItem] = []
        container = top
        for rel, r_prop in self.config.relations(dal.className()).items():
            rel_type = r_prop["type"]

            draw = rel_type in self.classes_to_draw or any(
                rel_type in self.config.superclasses(c, all=True)
                for c in self.classes_to_draw
            )

            rel_vals = getattr(dal, rel)
            if not rel_vals:
                continue
            if not isinstance(rel_vals, list):
                rel_vals = [rel_vals]

            if draw:
                rel_item = DrawItem(label=rel)
                container.append(rel_item)
                container = rel_item.children

            for r in rel_vals:
                r_state = self._calc_config_state(r, parent_state)
                children = self._config_items(r, r_state)
                if draw:
                    container.append(DrawItem(repr(r), r_state, children, source=r))
                else:
                    container.extend(children)
        return top

    def _render_config_branch(self, branch, dal, parent_state: State) -> None:
        """Recursively render configuration tree branches into ``branch``.

        :param branch: The Rich tree branch to render into
        :param dal: The DAL object to render
        :param parent_state: The parent's state for context
        """
        add_items(branch, self._config_items(dal, parent_state))

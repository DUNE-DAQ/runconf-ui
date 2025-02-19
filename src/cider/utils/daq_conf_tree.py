# Essentially the tree from https://github.com/DUNE-DAQ/daqconf/blob/develop/scripts/daqconf_inspector

import cider.interfaces.actions.actions as ca
from cider.interfaces.workflows.get_objects_in_session import GetObjectsInSessionAction
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from cider.interfaces.workflows.extract_system_info import SystemInfoExtractor


from rich.tree import Tree
from abc import ABC, abstractmethod


class DaqConfTreeBase(ABC):
    """
    Base class for the daq conf tree
    """

    def __init__(
        self,
        configuration: ConfigurationWrapper | None = None,
        session: str | None = None,
    ):
        """Constructor for the DaqConfTree class."""

        self._tree = Tree("[bold red]No Configuration Loaded")
        self._disabled_objs = []
        self.open_new_session(configuration, session)

    def open_new_session(
        self, configuration: ConfigurationWrapper, session: str | None
    ):
        """Open a new session."""
        self._configuration = configuration
        self._session = session

        if configuration is not None and session is not None:
            self.generate_tree()

    def print_tree(self):
        """Print the tree."""
        return self._tree

    @abstractmethod
    def generate_tree(self):
        pass


class DaqConfTree(DaqConfTreeBase):
    """
    Class to represent the daq configuration tree. This generates the full system view
    """

    def __init__(
        self,
        configuration: ConfigurationWrapper | None = None,
        session: str | None = None,
    ):
        """Constructor for the DaqConfTree class."""

        self._disabled_objs = []
        super().__init__(configuration, session)

    def generate_tree(self) -> Tree:
        """Generate the tree."""
        # Add the session
        self._tree = Tree(f"[bold red1] {self._session}")

        # We're now going to recurssively loop through relations to session
        session_dal = ca.GetDalObjectAction(self._configuration)(
            self._session, "Session"
        )

        self.build_tree(session_dal, self._tree, False)
        return self._tree

    def get_related_segments(self, segment):
        """
        Get related segments
        """
        class_name = ca.GetClassNameAction(self._configuration)(segment)

        # Inexplicably session labels its segments as "segments" and not "segment"
        if class_name == "Segment":
            return ca.GetAttributeAction(self._configuration)(segment, "segments")
        elif class_name == "Session":
            return [ca.GetAttributeAction(self._configuration)(segment, "segment")]
        else:
            raise ValueError(
                f"Invalid class {ca.GetClassNameAction(self._configuration)(segment)}"
            )

    def get_related_apps(self, segment):
        """
        Get related apps
        """
        return ca.GetAttributeAction(self._configuration)(segment, "applications")

    def build_tree(self, segment, tree_branch: Tree, is_disabled: bool = False):
        # Get segmeents

        # Recurssive logic
        if not self.get_related_segments(segment):
            return

        if self.get_related_segments(segment):
            segs = tree_branch.add("[bold dark_orange3]Segments")

        # Loop through segments
        for seg in self.get_related_segments(segment):
            seg_name = ca.GetAttributeAction(self._configuration)(seg, "id")

            if (
                ca.CheckIsDisabledAction(self._configuration)(seg, self._session)
                or is_disabled
            ):
                seg_disabled = True
                colour = "grey35"
                message = "DISABLED"
                self._disabled_objs.append(seg)

            else:
                seg_disabled = False
                colour = "green"
                message = "ENABLED"

            seg_name = f"[{colour}]{seg_name}   [bold]{message}"
            seg_branch = segs.add(f"{seg_name}")

            # Continue building tree until nothing left
            self.build_tree(seg, seg_branch, seg_disabled)

            self.add_apps(seg, seg_branch, seg_disabled)
        return segs

    def add_apps(self, seg, seg_branch, seg_disabled):

        # Get apps
        if not len(self.get_related_apps(seg)):
            return

        seg_apps = seg_branch.add("[bold deep_pink4]Applications")
        for app in self.get_related_apps(seg):

            app_name = ca.GetAttributeAction(self._configuration)(app, "id")

            if (
                ca.CheckIsDisabledAction(self._configuration)(app, self._session)
                or seg_disabled
            ):
                colour = "grey35"
                message = "DISABLED"
                self._disabled_objs.append(app)

            else:
                colour = "green"
                message = "ENABLED"

            app_name = f"[{colour}]{app_name}   [bold]{message}"

            seg_apps.add(app_name)

    @property
    def disabled_objs(self):
        return self._disabled_objs


class ComponentLevelTree(DaqConfTreeBase):
    """
    Class To Represent Multicomponent objects
    """

    def __init__(
        self,
        configuration: ConfigurationWrapper | None = None,
        session: str | None = None,
        system_info: dict = {},
        label: str = "",
        disabled_items=[],
    ):
        # System info dict
        self._system_info = system_info
        # Disabled items, obtained from DaqConfTree usually
        self._disabled_items = disabled_items
        # Extractor
        self._extractor = SystemInfoExtractor(configuration, session)
        # Label for the top level branch
        self._label = label

        super().__init__(configuration, session)

    def generate_tree(self):
        """
        Actually generate the full tree
        """
        self._tree = Tree(f"[bold deep_pink4] {self._label}")

        # Get the labels for each system system
        system_labels = list(self._system_info.keys())

        # Grab the session
        session_dal = ca.GetDalObjectAction(self._configuration)(
            self._session, "Session"
        )

        # Loop over each system
        for label in system_labels:
            system_enabled = self._system_info[label]["enabled"]
            if system_enabled:
                colour = "chartreuse4"
                text = "ENABLED"
            else:
                colour = "grey35"
                text = "DISABLED"

            # Full system tree
            system_tree = self._tree.add(f"[bold {colour}]{label}     {text}")

            # Loop over each subsystem
            for subsystem in self._system_info[label]["subsystems"]:
                # Check state of each object
                enabled = self._extractor.check_single_object_state(
                    subsystem, system_enabled
                )

                # Okay now we can grab each component
                if subsystem["type"] == "attribute":
                    specific_comps = GetObjectsInSessionAction(self._configuration)(
                        session_dal,
                        subsystem["class"],
                        subsystem.get("affected_objects", None),
                    )

                    system_name = subsystem["id"]

                elif (
                    subsystem["type"] == "component"
                    or subsystem["type"] == "relationship"
                ):
                    # Specific component
                    specific_comps = [
                        ca.GetDalObjectAction(self._configuration)(
                            subsystem["id"], subsystem["class"]
                        )
                    ]
                    system_name = ""

                    # Relationships need slightly special treatment
                    if subsystem["type"] == "relationship":
                        system_name += subsystem["relationship_name"]

                for c in specific_comps:
                    if enabled and c not in self._disabled_items:
                        colour = "chartreuse3"
                        text = "[bold]ENABLED"
                    else:
                        colour = "grey35"
                        text = "[bold]DISABLED"

                    system_tree.add(
                        f"[{colour}]{ca.GetAttributeAction(self._configuration)(c, 'id')} {system_name} {text}"
                    )

        return self._tree

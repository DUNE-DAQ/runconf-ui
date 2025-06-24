# Essentially the tree from https://github.com/DUNE-DAQ/daqconf/blob/develop/scripts/daqconf_inspector

import runconf_ui.daq_config_interfaces.actions.actions as ca
from runconf_ui.runconf_ui_configuration.object_extractors.detector_extractor import (
    DetectorExtractor,
)
from runconf_ui.utils.subsystem_status import SubsystemStatus

from runconf_ui.exceptions import CiderBadActionException

from rich.tree import Tree
from abc import ABC, abstractmethod
from runconf_ui.runconf_ui_controllers.runconf_ui_state import (
    ShifterInterfaceState,
)


class DaqConfTreeBase(ABC):
    """
    Base class for the daq conf tree
    """

    def __init__(
        self,
        application_controller: ShifterInterfaceState,
    ):
        """Constructor for the DaqConfTreeBase class."""

        self._application_controller = application_controller

        self._tree = Tree("[bold red]No Configuration Loaded")
        self._disabled_objs = []
        self.open_new_session()

    def open_new_session(self):
        """Open a new session."""

        if (
            self._application_controller.buffer_daq_config is not None
            and self._application_controller.session_name is not None
        ):
            self.generate_tree()

    def print_tree(self):
        """Print the tree."""
        return self._tree

    def get_text_colour_message(self, system_state: SubsystemStatus | None):

        if system_state == SubsystemStatus.ENABLED:
            colour = "chartreuse4"
        elif (
            system_state == SubsystemStatus.DISABLED
            or system_state == SubsystemStatus.TOP_LEVEL_DISABLED
        ):
            system_state = SubsystemStatus.DISABLED
            colour = "grey35"
        elif system_state == SubsystemStatus.PARTIALLY_ENABLED:
            colour = "dark_orange3"
        else:
            raise ValueError(f"Invalid state {system_state}")

        # Just so we can make it readable!
        return colour, system_state.name.replace("~", " ")

    @abstractmethod
    def generate_tree(self):
        pass


class ComponentLevelTree(DaqConfTreeBase):
    """
    After doing this, you may fix the identity used for this commit with:

        git commit --amend --reset-author

     1 file changed, 290 insertions(+), 109 deletions(-)
    henryi@beluga4 ~/sft/MaCh3 $ git push
    Enumerating objects: 7, done.
    Counting objects: 100% (7/7), done.
    Delta compression using up to 40 threads
    Compressing objects: 100% (4/4), done.
    Writing objects: 100% (4/4), 5.13 KiB | 1.03 MiB/s, done.
    Total 4 (delta 2), reused 0 (delta 0), pack-reused 0
    remote: Resolving deltas: 100% (2/2), completed with 2 local objects.
    To ssh://github.com/mach3-software/MaCh3.git
       c3ea0d82..51eafbb4  hwallace/autocorr_avg -> hwallace/autocorr_avg
    henryi@beluga4 ~/sft/MaCh3 $ ./install/bin/PlotMCMCDiag ~/sft/MaCh3Tutorial/studies/Adapt/T2K/mcmc_Adapt_T2K_all_on_long_MCMC_Diag.root
    ./install/bin/PlotMCMCDiag: error while loading shared libraries: libPlotting.so: cannot open shared object file: No such file or directory
    henryi@beluga4 ~/sft/MaCh3 $ source install/bin/setup.MaCh3.sh
    Sourcing NuOscillator
    henryi@beluga4 ~/sft/MaCh3 $ ./install/bin/PlotMCMCDiag ~/sft/MaCh3Tutorial/studies/Adapt/T2K/mcmc_Adapt_T2K_all_on_long_MCMC_Diag.root
    [PlotMCMCDiag.cpp][info] Processed 27 parameters from /home/henryi/sft/MaCh3Tutorial/studies/Adapt/T2K/mcmc_Adapt_T2K_all_on_long_MCMC_Diag.root files
    Info in <TCanvas::Print>: pdf file Average_Auto_Corr.pdf has been created
    henryi@beluga4 ~/sft/MaCh3 $ ./install/bin/PlotMCMCDiag ~/sft/MaCh3Tutorial/studies/Adapt/T2K/mcmc_Adapt_T2K_all_on_long_MCMC_Diag.root ~/sft/
    CPM.cmake/             ENV/                   general_env/           HMCMC/                 MaCh3/                 MaCh3_Patches/         MaCh3-PythonUtils/     MaCh3Tutorial/         MaCh3Tutorial_Default/
    henryi@beluga4 ~/sft/MaCh3 $ ./install/bin/PlotMCMCDiag ~/sft/MaCh3Tutorial/studies/Adapt/T2K/mcmc_Adapt_T2K_all_on_long_MCMC_Diag.root ~/sft/MaCh3
    MaCh3/                 MaCh3_Patches/         MaCh3-PythonUtils/     MaCh3Tutorial/         MaCh3Tutorial_Default/
    henryi@beluga4 ~/sft/MaCh3 $ ./install/bin/PlotMCMCDiag ~/sft/MaCh3Tutorial/studies/Adapt/T2K/mcmc_Adapt_T2K_all_on_long_MCMC_Diag.root ~/sft/MaCh3Tutorial
    MaCh3Tutorial/         MaCh3Tutorial_Default/
    henryi@beluga4 ~/sft/MaCh3 $ ./install/bin/PlotMCMCDiag ~/sft/MaCh3Tutorial/studies/Adapt/T2K/mcmc_Adapt_T2K_all_on_long_MCMC_Diag.root ~/sft/MaCh3Tutorial/
    build/            cmake/            Doc/              .git/             .gitignore        LICENSE.txt       plotting/         requirements.txt  splines/          Tutorial/         Utils/
    CIValidations/    CMakeLists.txt    env.sh            .github/          install/          .mailmap          README.md         samplePDF/        studies/          TutorialConfigs/
    henryi@beluga4 ~/sft/MaCh3 $ ./install/bin/PlotMCMCDiag ~/sft/MaCh3Tutorial/studies/Adapt/T2K/mcmc_Adapt_T2K_all_on_long_MCMC_Diag.root ~/sft/MaCh3Tutorial/studies/
    Adapt/   adhoc/   configs/ NoAdapt/ scripts/
    henryi@beluga4 ~/sft/MaCh3 $ ./install/bin/PlotMCMCDiag ~/sft/MaCh3Tutorial/studies/Adapt/T2K/mcmc_Adapt_T2K_all_on_long_MCMC_Diag.root ~/sft/MaCh3Tutorial/studies/
    Adapt/   adhoc/   configs/ NoAdapt/ scripts/
        Class to represent multi-component objects in a tree structure.
    """

    def __init__(
        self,
        application_controller: ShifterInterfaceState,
        extractor: DetectorExtractor | None = None,
        disabled_items=[],
    ):
        self._extractor = extractor
        self._disabled_items = disabled_items

        super().__init__(application_controller)

    def generate_tree(self) -> Tree:
        """Generate the tree structure for the system."""
        if self._extractor is None:
            self._tree = Tree("[bold red1] No Configuration Loaded")
        else:
            self.initialise_tree()
        return self._tree

    def initialise_tree(self):
        self._tree = Tree(
            f"[bold red1] {self._extractor.system_info.get('view_panel', 'Unknown')}"
        )

        for system in self._extractor.systems:
            # Start with is_disabled=False for the top-level system
            try:
                self._add_system_to_tree(system, is_disabled=False)
            except CiderBadActionException:
                continue
            except Exception as e:
                raise e

    def _add_system_to_tree(self, system, is_disabled: bool):
        """Add a system and its subsystems to the tree."""
        # If the system is disabled, propagate the disabled state to all children

        state = self._extractor.get_state(system.system_name)

        # DON'T ADD
        if state == SubsystemStatus.STATE_NOT_DEFINED:
            return

        system_disabled = is_disabled or state == SubsystemStatus.DISABLED

        colour, message = self.get_text_colour_message(state)

        system_tree = self._tree.add(f"[{colour}]{system.system_name} [bold]{message}")

        for subsyst in system.system_names[::-1]:
            self._add_subsystem_to_tree(system, subsyst, system_tree, system_disabled)

    def _add_subsystem_to_tree(self, system, subsyst, system_tree, is_disabled: bool):
        """Add a subsystem and its components to the tree."""
        # If the subsystem is disabled, propagate the disabled state to all children
        state = system.get_state(subsyst)

        if state == SubsystemStatus.STATE_NOT_DEFINED:
            return

        subsystem_disabled = is_disabled or (state == SubsystemStatus.DISABLED)
        colour, message = self.get_text_colour_message(
            SubsystemStatus.DISABLED if subsystem_disabled else state
        )

        if subsyst != system.system_names[-1]:
            subsyst_tree = system_tree.add(f"[{colour}]{subsyst}   [bold]{message}")
        else:
            subsyst_tree = system_tree

        self._add_components_to_tree(system, subsyst, subsyst_tree, subsystem_disabled)
        self._add_attributes_to_tree(system, subsyst, subsyst_tree, subsystem_disabled)

    def _add_components_to_tree(self, system, subsyst, subsyst_tree, is_disabled: bool):
        """Add components of a subsystem to the tree."""
        for comp in system.get_components(subsyst):
            if subsyst == system.system_names[-1] and comp.system_name is not None:
                continue

            state = comp.get_state()

            if state == SubsystemStatus.STATE_NOT_DEFINED:
                continue

            component_disabled = (
                is_disabled
                or (state == SubsystemStatus.DISABLED)
                or comp.get_dal() in self._disabled_items
            )

            colour, message = self.get_text_colour_message(
                SubsystemStatus.DISABLED if component_disabled else state
            )
            subsyst_tree.add(f"[{colour}]{comp.system_id}   [bold]{message}")

    def _get_unique_attribute_objects(self, system, subsyst):
        """Get unique attribute objects for a subsystem, ensuring they are referenced by at least one attribute."""
        attribute_objs = set()
        for attr in system.get_attributes(subsyst):
            affected_objs = attr.get_affected_object_dals()
            if affected_objs:  # Only include attributes that affect objects
                attribute_objs.update(affected_objs)
        return list(attribute_objs)

    def _build_attribute_tree(self, attribute_objs, system_disabled: bool = False):
        """Build a tree structure for attribute objects, only including those with attributes."""
        attribute_tree = {}
        for obj in attribute_objs:
            obj_id = ca.GetAttributeAction(
                self._application_controller.buffer_daq_config
            )(obj, "id")

            # Check if the attribute object is in the disabled list
            obj_disabled = obj in self._extractor.get_disabled_dals() or system_disabled
            status = (
                SubsystemStatus.DISABLED if obj_disabled else SubsystemStatus.ENABLED
            )
            colour, _ = self.get_text_colour_message(status)

            # Only add to tree if there are attributes for this object
            attribute_tree[obj_id] = Tree(f"[{colour}]{obj_id}")

        return attribute_tree

    def _add_attributes_to_tree(self, system, subsyst, subsyst_tree, is_disabled: bool):
        """Add attributes and their affected objects to the tree, skipping empty objects."""
        attribute_objs = self._get_unique_attribute_objects(system, subsyst)
        # Only proceed if there are attributes for this subsystem
        if not attribute_objs:
            return

        attribute_tree = self._build_attribute_tree(attribute_objs, is_disabled)
        has_attributes = False  # Track if any attributes were added

        for attr in system.get_attributes(subsyst):
            if subsyst == system.system_names[-1] and attr.system_name is not None:
                continue

            affected_objs = attr.get_affected_object_names()
            if affected_objs:  # Only process attributes that affect objects
                self._add_attribute_to_tree(attr, attribute_tree, is_disabled)
                has_attributes = True

        # Only add the attribute tree if it contains attributes
        if has_attributes:
            for attr_tree in attribute_tree.values():
                subsyst_tree.add(attr_tree)

    def _add_attribute_to_tree(self, attr, attribute_tree, is_disabled: bool):
        """Add an attribute and its affected objects to the attribute tree."""

        for obj_name in attr.get_affected_object_names():
            if obj_name in attribute_tree:
                # If the attribute object is in the disabled list, mark it as disabled
                obj_disabled = (
                    is_disabled
                    or (attr.get_state_for_obj(obj_name) == SubsystemStatus.DISABLED)
                    or (attr.get_affected_object(obj_name) in self._disabled_items)
                )
                colour, message = self.get_text_colour_message(
                    SubsystemStatus.DISABLED
                    if obj_disabled
                    else attr.get_state_for_obj(obj_name)
                )
                attribute_tree[obj_name].add(
                    f"[{colour}]{attr.system_id}   [bold]{message}"
                )

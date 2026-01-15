import logging

from textual.screen import Screen

from runconf_ui.daq_config_interfaces.daq_tree_tools.daq_full_tree import DaqFullTree
from runconf_ui.runconf_ui_controllers.runconf_ui_state import ShifterInterfaceState
from runconf_ui.widgets.multicomponent_panel import MultiComponentEnableDisablePanel


class DaqTreeManager:
    def __init__(self, application_controller: ShifterInterfaceState):
        self._application_controller = application_controller

    def update_all_trees(self, screen: Screen):        
        """Update all tree views in the screen"""
        logging.debug("Updating all trees in the screen")
        # main_tree = DaqConfTree(self._application_controller)
        main_tree = DaqFullTree(self._application_controller)
        main_tree.generate_tree()
        screen.query_one("#tree_view_full").update(main_tree.print_tree())
        disabled = main_tree.disabled_objs
        logging.debug(f"Disabled objects: {disabled}")

        for panel in screen.query("EnableDisablePanel"):
            self._application_controller.current_state[panel.id] = (
                panel.get_current_states()
            )

            if isinstance(panel, MultiComponentEnableDisablePanel) and panel:
                panel.update_disabled(disabled)
                self.update_component_tree(screen, panel)

            panel.update_button_styles()

    def update_component_tree(self, screen, panel: MultiComponentEnableDisablePanel):
        t = panel.get_tree()
        if t is None:
            return
        
        screen.query_one(
            f"#tree_view_{panel.id.replace('_subsystem_panel', '')}"
        ).update(t.print_tree())

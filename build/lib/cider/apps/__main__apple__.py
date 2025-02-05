# APPLE: Accessible Platform for Plain and Lightweight Editing

from cider.screens.disable_object_screen import DisableObjectScreen
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from textual.app import App
from textual.driver import Driver


class Apple(App):    
    
    def __init__(self, configuration, driver_class: type[Driver] | None = None, css_path: str | None = None, watch_css: bool = False, ansi_color: bool = False):
        super().__init__(driver_class, css_path, watch_css, ansi_color)
        
        self._configuration = configuration
    
    def on_mount(self):
        self.install_screen(DisableObjectScreen(self._configuration, "fakedata-session"), name="main")
        self.push_screen("main")

def main():
    
    CONFIGURATION_PATH = "/home/hwallace/scratch/dune_software/daq/daq_work_areas/NFD_DEV_241218_A9/nd_generated_file/integtest-session-resolved.data.xml"
    
    app = Apple(ConfigurationWrapper(CONFIGURATION_PATH))
    app.run()
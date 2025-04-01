# Just needs to be the widgets, we will wire in the functionality in a bit

from typing import Iterable, Any, List
from textual.message import Message
from textual.visual import SupportsVisual
from textual.widgets import Button, Static, Select
from textual.containers import Grid
from textual.widgets._select import NoSelection
from rich.console import ConsoleRenderable, RichCast
from textual import on
from pathlib import Path
import logging
import traceback

from cider.utils.management_interface import LocalManagementInterface, RemoteManagementInterface
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper
from cider.interfaces.controller.application_controller import ShifterInterfaceState


class DAQSelectMenu(Select):
    def __init__(
        self,
        options: Iterable[tuple[ConsoleRenderable | RichCast | str, Any]],
        management_interface: Any,
        *,
        prompt: str = "Select",
        allow_blank: bool = True,
        value: Any | NoSelection = ...,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
        tooltip: ConsoleRenderable | RichCast | str | None = None
    ):

        # store default value
        self._default_value = value

        # Check if the value is in the options
        value = self.check_options(options, value)

        super().__init__(
            options,
            prompt=prompt,
            allow_blank=allow_blank,
            value=value,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
            tooltip=tooltip,
        )

        self._management_interface = management_interface

        # Disable the select if there's only one option
        if len(self._options) == 1:
            self.value = self._options[0][1]
            self.disabled = True

    @classmethod
    def check_options(cls, options: Iterable[tuple[ConsoleRenderable | RichCast | str, Any]], default: Any | NoSelection):
        """
        Check if the options are valid
        """
        if default in [i[0] for i in options]:
            return default

        return Select.BLANK
        
class SelectDAQVersion(DAQSelectMenu):
    """
    Top level DAQ version select menu
    """

    def __init__(
        self,
        management_interface: Any,
        *,
        prompt: str = "Select",
        allow_blank: bool = True,
        value: Any | NoSelection = ...,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
        tooltip: ConsoleRenderable | RichCast | str | None = None
    ):
        
        options_list = management_interface.get_daq_versions()
        
        # We need to correctly format options
        options = [(str(Path(o).name), o) for o in options_list]
        
        super().__init__(
            options,
            management_interface=management_interface,
            prompt=prompt,
            allow_blank=allow_blank,
            value=value,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
            tooltip=tooltip,
        )
        
        if self.value != NoSelection:
            self._management_interface.set_version(self.value)
        
    def on_select_changed(self, event: Select.Changed) -> None:
        self._management_interface.set_version(event.value)
        self.post_message(self.DAQVersionSelected(event.value))

    class DAQVersionSelected(Message):
        def __init__(self, version: str):
            super().__init__()
            self.version = version


class SelectDAQConfiguration(DAQSelectMenu):
    """
    Secondary DAQ select menu
    """
    def __init__(
        self,
        management_interface: Any,
        *,
        prompt: str = "Select",
        allow_blank: bool = True,
        value: Any | NoSelection = ...,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
        tooltip: ConsoleRenderable | RichCast | str | None = None
    ):
        
        # Correctly format options
        options = [(m, m) for m in management_interface.get_configurations()]
        
        super().__init__(
            options,
            management_interface=management_interface,
            prompt=prompt,
            allow_blank=allow_blank,
            value=value,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
            tooltip=tooltip,
        )

    def update_version(self, version: str):
        self._management_interface.set_version(version)
        options = self._management_interface.get_configurations()

        if not options:
            self.disabled = True
            self.value = NoSelection
            return
            
        self.disabled = False
        self._value = self.check_options(options, self._default_value)
        self.set_options(options)

    def on_select_changed(self, event: Select.Changed) -> None:
        self.post_message(self.DAQConfigurationSelected(event.value))

    def set_options(self, options: List[str]):
        options = [(m, m) for m in options]
        super().set_options(options)

    class DAQConfigurationSelected(Message):
        def __init__(self, configuration: str | NoSelection):
            super().__init__()
            self.configuration = configuration


class FilePanelWidget(Static):
    def __init__(self, app_controller: ShifterInterfaceState, content: ConsoleRenderable | RichCast | str | SupportsVisual = "", *, expand: bool = False, shrink: bool = False, markup: bool = True, name: str | None = None, id: str | None = None, classes: str | None = None, disabled: bool = False) -> None:
        super().__init__(content, expand=expand, shrink=shrink, markup=markup, name=name, id=id, classes=classes, disabled=disabled)
    
        self._app_controller = app_controller
    
        if app_controller.use_local:
            self._management_interface = LocalManagementInterface(self._app_controller)
            self._daq_version_message = "Local DAQ Repository"
        else:
            self._management_interface = RemoteManagementInterface(self._app_controller)
            self._daq_version_message = "Remote DAQ Repository"
    
    def compose(self):
        with Grid(id="file_io_panel_grid"):
            yield SelectDAQVersion(self._management_interface, classes="file_select", id="daq_version_select")
            yield SelectDAQConfiguration(self._management_interface, classes="file_select", id="daq_configuration_select")
            yield Button("Open", id="open_file_button", disabled=True, classes="file_io_button")
            yield Static("[bold medium_violet_red]   No file loaded\n  ", id="file_io_panel_message")

    @property
    def management_interface(self):
        return self._management_interface

    @on(SelectDAQVersion.DAQVersionSelected)
    def handle_daq_version_selected(self, event: SelectDAQVersion.DAQVersionSelected) -> None:
        self.query_one("#daq_configuration_select").update_version(event.version)


    @on(SelectDAQConfiguration.DAQConfigurationSelected)
    def handle_daq_configuration_selected(self, event: SelectDAQConfiguration.DAQConfigurationSelected) -> None:
        if event.configuration == NoSelection:
            
            self._app_controller.session_name = None
            self._app_controller.oks_configuration = None
            self._app_controller.dummy_oks_configuration = None

            self.post_message(self.FileDeconfigured())
            self.query_one("#open_file_button").disabled = True            
            return
        
        self.query_one("#open_file_button").disabled = False

    @on(Button.Pressed)
    def handle_open_file_button_pressed(self) -> None:
        # Get the selected configuration
        selected_configuration = self.query_one("#daq_configuration_select").value
        logging.info(f"{selected_configuration}")

        if selected_configuration == NoSelection:
            self.post_message(self.FileDeconfigured())
            return
        # Open the file
        try:
            daq_config_file = self._management_interface.open_file(selected_configuration)
            self._app_controller.oks_configuration = daq_config_file.file_name
            self._app_controller.session_name = self._management_interface.find_session(daq_config_file.file_name)
            
            
            self.query_one("#file_io_panel_message").update(
            f"   [bold green]Current Config[/bold green]: [deep_pink4]{self._app_controller.oks_configuration}[/deep_pink4]\n   [bold green]Session[/bold green]:  [deep_pink4]{self._app_controller.session_name}"
        )
            self.post_message(self.FileSelected())
        
    
        except Exception:
            logging.error(f"{traceback.format_exc()}")
            self.post_message(self.FileNotFound(selected_configuration))

    class FileSelected(Message):
        ...
            
    class FileNotFound(Message):
        def __init__(self, file_path: Path):
            super().__init__()
            self.file_path = file_path

    class FileDeconfigured(Message):
        ...            

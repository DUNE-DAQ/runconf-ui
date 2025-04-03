# Just needs to be the widgets, we will wire in the functionality in a bit

from typing import Iterable, Any, List
from textual.message import Message
from textual.visual import SupportsVisual
from textual.widgets import Button, Static, Select
from textual.containers import Grid, ScrollableContainer
from textual.widgets._select import NoSelection
from rich.console import ConsoleRenderable, RichCast
from textual import on
from pathlib import Path
import logging
import traceback

from runconf_ui.utils.management_interface import (
    LocalManagementInterface,
    RemoteManagementInterface,
)
from runconf_ui.interfaces.controller.application_controller import ShifterInterfaceState


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
        tooltip: ConsoleRenderable | RichCast | str | None = None,
    ):

        # store default value
        self._default_value = value

        # Check if the value is in the options
        # Disable the select if there's only one option
        if len(options) == 1:
            value = self.check_options(options, options[0][1])
            disabled = True
        else:
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
        logging.info(f"Select initialized with value: {self._value}")

    @classmethod
    def check_options(
        cls,
        options: Iterable[tuple[ConsoleRenderable | RichCast | str, Any]],
        default: Any | NoSelection,
    ):
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
        tooltip: ConsoleRenderable | RichCast | str | None = None,
    ):

        options_list = management_interface.get_daq_versions()
        # We need to correctly format options
        options = [(str(Path(o).name), o) for o in options_list]

        if len(options) == 1:
            management_interface.set_version(options_list[0])

        default_val = self.check_options(options, value)

        super().__init__(
            options,
            management_interface=management_interface,
            prompt=prompt,
            allow_blank=allow_blank,
            value=default_val,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
            tooltip=tooltip,
        )

        if self.value != NoSelection:
            self._management_interface.set_version(self.value)

    def on_select_changed(self, event: Select.Changed) -> None:
        if self._management_interface.daq_version == event.value:
            logging.info("DAQ version already selected")
            return

        self._management_interface.set_version(event.value)
        self.post_message(self.DAQVersionSelected())

    class DAQVersionSelected(Message): ...


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
        default_version: str | None = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
        tooltip: ConsoleRenderable | RichCast | str | None = None,
    ):

        # Real hack
        # Correctly format options

        if len(management_interface.get_daq_versions()) == 1:
            management_interface.set_version(management_interface.get_daq_versions()[0])
            disabled = True
            options = [
                (str(Path(m).name), m)
                for m in management_interface.get_configurations()
            ]
            value = options[0][1]

        elif default_version in management_interface.get_daq_versions():
            management_interface.set_version(default_version)
            options = [
                (str(Path(m).name), m)
                for m in management_interface.get_configurations()
            ]

            value = self.check_options(options, value)

        else:
            options = management_interface.get_configurations()

        self._current_version = management_interface.daq_version

        if not options:
            disabled = True

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

    def update_version(self):
        if self._management_interface.daq_version == self._current_version:
            logging.info(f"DAQ version already selected {self._current_version}")
            return

        self._current_version = self._management_interface.daq_version

        options = self._management_interface.get_configurations()

        if not options:
            self.disabled = True
            self.set_options([])
            self._value = Select.BLANK
            return

        self.disabled = False
        self.set_options(options)

    def on_select_changed(self, event: Select.Changed) -> None:
        self.post_message(self.DAQConfigurationSelected(event.value))

    def set_options(self, options: List[str]):
        options = [(str(Path(m).name), m) for m in options]
        super().set_options(options)

    class DAQConfigurationSelected(Message):
        def __init__(self, configuration: str | NoSelection):
            super().__init__()
            self.configuration = configuration


class FilePanelWidget(Static):
    def __init__(
        self,
        app_controller: ShifterInterfaceState,
        content: ConsoleRenderable | RichCast | str | SupportsVisual = "",
        *,
        expand: bool = False,
        shrink: bool = False,
        markup: bool = True,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(
            content,
            expand=expand,
            shrink=shrink,
            markup=markup,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )

        self._app_controller = app_controller

        if app_controller.use_local:
            self._management_interface = LocalManagementInterface(self._app_controller)
            self._daq_version_message = "Select database in local DAQ Repository"
        else:
            self._management_interface = RemoteManagementInterface(self._app_controller)
            self._daq_version_message = "Select DAQ configuration version"

    def compose(self):
        default_config = self._app_controller.interface_config.default_daq_config
        default_version = self._app_controller.interface_config.default_version

        s = SelectDAQConfiguration(
            self._management_interface,
            prompt="Select DAQ configuration",
            classes="file_select",
            id="daq_configuration_select",
            value=default_config,
            default_version=default_version,
        )

        with Grid(id="file_io_panel_grid"):
            yield SelectDAQVersion(
                self._management_interface,
                prompt=f"{self._daq_version_message}",
                classes="file_select",
                id="daq_version_select",
                value=default_version,
            )
            yield s
            yield Button(
                "Open", id="open_file_button", disabled=True, classes="file_io_button"
            )
            with ScrollableContainer(id="file_io_panel_message"):
                yield Static(
                        "[bold medium_violet_red]   No file loaded\n  ",
                        id="file_io_panel_message_static",
                        shrink=True)

    @property
    def management_interface(self):
        return self._management_interface

    @on(SelectDAQVersion.DAQVersionSelected)
    def handle_daq_version_selected(self) -> None:
        logging.info("selected version")

        self.query_one("#daq_configuration_select").update_version()

    @on(SelectDAQConfiguration.DAQConfigurationSelected)
    def handle_daq_configuration_selected(
        self, event: SelectDAQConfiguration.DAQConfigurationSelected
    ) -> None:
        if event.configuration == Select.BLANK:

            self._app_controller.session_name = None
            self._app_controller.oks_configuration = None
            self._app_controller.dummy_oks_configuration = None

            # self.post_message(self.FileDeconfigured())
            self.query_one("#open_file_button").disabled = True
            return

        self.query_one("#open_file_button").disabled = False

    @on(Button.Pressed)
    def handle_open_file_button_pressed(self) -> None:
        # Get the selected configuration
        selected_configuration = self.query_one("#daq_configuration_select").value
        logging.info(f"{selected_configuration}")

        if selected_configuration == Select.BLANK:
            self.post_message(self.FileDeconfigured())
            return
        # Open the file
        try:
            daq_config_file = self._management_interface.open_file(
                selected_configuration
            )

            self.post_message(self.FileSelected())

        except Exception:
            logging.error(f"{traceback.format_exc()}")
            self.post_message(self.FileNotFound(selected_configuration))
            return

        self._app_controller.oks_configuration = daq_config_file.file_name
        self._app_controller.session_name = self._management_interface.find_session(
            daq_config_file.file_name
        )
        self.query_one("#file_io_panel_message_static").update(
            f"      [bold green]DAQ Version[/bold green]:  [deep_pink4]{self._management_interface.daq_version}[/deep_pink4]\n"
            f"      [bold green]DAQ Config[/bold green]:  [deep_pink4]{selected_configuration}[/deep_pink4]\n"
            f"      [bold green]Current Config File[/bold green]: [deep_pink4]{self._app_controller.oks_configuration}[/deep_pink4]\n"
            f"      [bold green]Session in Config[/bold green]:  [deep_pink4]{self._app_controller.session_name}\n"
        )

    class FileSelected(Message): ...

    class FileNotFound(Message):
        def __init__(self, file_path: Path):
            super().__init__()
            self.file_path = file_path

    class FileDeconfigured(Message): ...


# develop-mroda-pds

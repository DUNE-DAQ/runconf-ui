from textual.screen import Screen
from textual.containers import Container, Grid
from textual.widgets import Button, Select, Label
from textual.message import Message

from typing import Any, List
import datetime
import sys

import conffwk


class ShifterSelectionScreen(Screen):

    def __init__(
        self,
        session_folder: List[str],
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self._select_file = SelectFile(
            session_folder, session_only=True, id="select_file"
        )
        self._select_session = SelectSession(id="select_session")

        # Mega uber hack
        self._config_controller = ConfigurationController()
        self._logger = RichLogWError()

        self._selected_config_name = ""
        self._selected_session_name = ""

    def compose(self):

        yield Grid(
            self._select_file,
            self._select_session,
            Button(
                id="create_config", label="Generate Configuration", variant="success"
            ),
        )

        yield self._config_controller
        yield self._logger

    def on_select_changed(self, event: Select.Changed):
        if event.select.id == "config_file_select":
            # Put in exception block to stop crash on nothing selected
            # hack for now, plan to refactor everything in a bit
            try:
                self._selected_config_name: str = event.value[0]
                self._select_session.change_config(self._selected_config_name)
                self._selected_session_name = ""

            except Exception as e:
                raise e

        elif event.select.id == "session_select":
            self._selected_session_name: str = getattr(event.value, "id")

    def create_config(self):
        if not self._selected_config_name:
            raise Exception(f"Couldnt find {self._selected_config_name}")
        elif not self._selected_session_name:
            raise Exception(f"Couldnt find {self._selected_session_name}")

        db_consolidator = ConsolidateDB(
            self._selected_config_name, self._selected_session_name, "Session"
        )
        db_consolidator()

        self._config_controller.new_handler_from_str(
            db_consolidator.get_generated_config()
        )

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "create_config":
            self.create_config()
            self.app.push_screen("disable")


class ConsolidateDB:
    # YES THIS EXiSTS
    def __init__(
        self,
        current_config_name: str,
        top_level_object_name: str,
        top_level_object_class: str,
    ):
        self._top_level_object_name = top_level_object_name
        self._top_level_object_class = top_level_object_class

        self._current_config_name = current_config_name
        self._new_config_name = self.create_timestamped_file_string(current_config_name)

    def get_generated_config(self):
        return self._new_config_name

    # I need a utils package...
    @classmethod
    def create_timestamped_file_string(cls, file_path: str) -> str:
        basepath = file_path.strip(".data.xml")
        ts = datetime.datetime.now().isoformat()

        ts = ts.replace(":", ".")

        return f"{basepath}_{ts}.data.xml"
        # return "test_config.data.xml"

    #
    def get_all_includes(self, db, file):
        includes = db.get_includes(file)
        for include in includes:
            if "data.xml" in include:
                includes += self.get_all_includes(db, include)

        return list(set(includes))

    def open_files(self) -> conffwk.Configuration:
        database = conffwk.Configuration(f"oksconflibs:{self._current_config_name}")

        # Grab included schema
        includes = [
            i for i in self.get_all_includes(database, None) if ".schema.xml" in i
        ]

        new_database = conffwk.Configuration("oksconflibs")
        new_database.create_db(self._new_config_name, includes)

        new_database.commit()

    # Now the fun bit
    def populate_configuration(self):
        sys.setrecursionlimit(10000)  # for example

        # Now we make the configuration
        # TODO: Simplify all of this
        current_configuration = ConfigurationHandler(self._current_config_name)
        new_configuration = ConfigurationHandler(self._new_config_name)

        # Now we need to get the top level DAL [usually a session]
        top_level_dal = current_configuration.get_dal(
            self._top_level_object_class, self._top_level_object_name
        )
        new_configuration.copy_conf_obj(top_level_dal)

        related_objs = self.__populate_configuration(
            current_configuration, top_level_dal
        )
        print(related_objs)

        # Now we just need to make sure everything's unique
        related_objs = list(set(related_objs))

        # Now we write to the configuration
        for d in related_objs:
            new_configuration.copy_conf_obj(d)

        new_configuration.commit(f"Copied from {self._new_config_name}")

    def __populate_configuration(self, configuration, dal_obj):

        related_objs = configuration.get_relationships_for_conf_object(dal_obj)

        relation_list = []
        for r in related_objs:
            for dal_list in list(r.values())[0]:
                if not isinstance(dal_list, list):
                    dal_list = [dal_list]

                if len(dal_list) == 0:
                    return

                for d in dal_list:
                    relation_list.append(d)
                    relation_list += list(
                        self.__populate_configuration(configuration, d)
                        for d in dal_list
                    )[0]

        return relation_list

    def __call__(self) -> Any:
        self.open_files()
        self.populate_configuration()

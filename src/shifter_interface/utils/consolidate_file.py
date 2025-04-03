from runconf_ui.interfaces.controller.config_wrapper import ConfigurationWrapper

from runconf_ui.interfaces.actions.actions import (
    GetDalObjectAction,
    CopyDalAction,
    GetRelatedDalsAction,
)
from typing import Any

import sys
import os


class ConsolidateFile:
    """
    File consolidator. Moves all objects in a session into a single .data.xml database
    """

    def __init__(
        self,
        current_config_name: str,
        top_level_object_name: str,
        top_level_object_class: str,
        new_config_name: str,
    ):

        self._top_level_object_name = top_level_object_name
        self._top_level_object_class = top_level_object_class

        self._current_config_name = current_config_name
        self._new_config_name = new_config_name

        if os.path.isfile(f"{self._new_config_name}"):
            os.remove(f"{self._new_config_name}")

    def get_generated_config(self):
        return self._new_config_name

    def get_all_includes(self, db, file):
        includes = db.get_includes(file)
        for include in includes:
            if "data.xml" in include:
                includes += self.get_all_includes(db, include)

        return list(set(includes))

    def open_files(self) -> None:
        database = ConfigurationWrapper(f"{self._current_config_name}")

        # Grab included schema
        includes = [
            i for i in self.get_all_includes(database, None) if ".schema.xml" in i
        ]

        new_database = ConfigurationWrapper("")
        new_database.create_db(self._new_config_name, includes)

        new_database.commit()

    # Now the fun bit
    def populate_configuration(self):
        sys.setrecursionlimit(10000)  # for example

        # Now we make the configuration
        # TODO: Simplify all of this
        current_configuration = ConfigurationWrapper(self._current_config_name)
        new_configuration = ConfigurationWrapper(self._new_config_name)

        # Now we need to get the top level DAL [usually a session]
        top_level_dal = GetDalObjectAction(current_configuration)(
            self._top_level_object_name, self._top_level_object_class
        )

        CopyDalAction(new_configuration)(top_level_dal)

        related_objs = self.__populate_configuration(
            current_configuration, top_level_dal
        )

        # Now we just need to make sure everything's unique
        related_objs = list(set(related_objs))

        # Now we write to the configuration
        for d in related_objs:
            CopyDalAction(new_configuration)(d)

        new_configuration.commit(f"Copied from {self._new_config_name}")

    def __populate_configuration(self, configuration, dal_obj):

        related_objs = GetRelatedDalsAction(configuration)(dal_obj)

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

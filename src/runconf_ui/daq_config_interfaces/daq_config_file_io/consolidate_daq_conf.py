import os
import sys
from typing import Any

from runconf_ui.daq_config_interfaces.actions.actions import (
    CommitConfigurationAction,
    CopyDalAction,
    GetAllDalsAction,
    GetDalObjectAction,
    GetRelatedDalsAction,
)
from runconf_ui.daq_config_interfaces.daq_config_file_io.daq_config_wrapper import (
    DaqConfigurationWrapper,
)


class ConsolidateDAQConf:
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
        database = DaqConfigurationWrapper(f"{self._current_config_name}")

        # Grab included schema
        includes = [
            i for i in self.get_all_includes(database, None) if ".schema.xml" in i
        ]

        new_database = DaqConfigurationWrapper("")
        new_database.create_db(self._new_config_name, includes)

        new_database.commit()

    # Now the fun bit
    def populate_configuration(self):
        sys.setrecursionlimit(10000)  # for example

        # Now we make the configuration
        # TODO: Simplify all of this
        current_configuration = DaqConfigurationWrapper(self._current_config_name)
        new_configuration = DaqConfigurationWrapper(self._new_config_name)

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
            for dal_list in next(iter(r.values())):
                if not isinstance(dal_list, list):
                    dal_list = [dal_list]

                if len(dal_list) == 0:
                    return None

                for d in dal_list:
                    relation_list.append(d)
                    relation_list += next([
                        self.__populate_configuration(configuration, d)
                        for d in dal_list]
                    )

        return relation_list

    def fill_all(self) -> None:
        """
        Fill the configuration with all objects in the session.
        """
        current_configuration = DaqConfigurationWrapper(self._current_config_name)
        new_configuration = DaqConfigurationWrapper(self._new_config_name)

        for dal in GetAllDalsAction(current_configuration)():
            CopyDalAction(new_configuration)(dal)

        CommitConfigurationAction(new_configuration)(
            f"Consolidated from {self._current_config_name}"
        )

    def __call__(self) -> Any:        
        self.open_files()
        # self.populate_configuration()
        self.fill_all()

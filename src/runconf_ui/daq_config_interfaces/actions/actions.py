from runconf_ui.daq_config_interfaces.actions.action_interfaces import ActionInterface
from runconf_ui.daq_config_interfaces.daq_config_file_io.daq_config_wrapper import (
    DaqConfigurationWrapper,
)
import shutil

"""
A collection of simple actions on a configuration. These should take a single configuration
and then be able to repeatedly perform a single operation on it
"""


# Chainable actions
class GetDalObjectAction(ActionInterface):
    def action(self, conf_obj_id: str, conf_obj_class: str):
        """
        Gets DAL object from configuration
        """
        conf_obj = self._daq_configuration.get_dal(conf_obj_class, conf_obj_id)
        return conf_obj


class ChangeAttributeAction(ActionInterface):
    def action(self, dal, attr_name, attr_value, append: bool = False):
        """
        Change object attribute
        """
        if append:
            attr_value = getattr(dal, attr_name).append(attr_value)
        setattr(dal, attr_name, attr_value)
        return dal


class UnloadConfigurationAction(ActionInterface):
    def action(self):
        """
        Unload configuration
        """
        self._daq_configuration.unload()
        return None


class UpdateDalAction(ActionInterface):
    """
    Update object in configuration
    """

    def action(self, dal):
        self._daq_configuration.update_dal(dal)
        return dal


class DestroyDalAction(ActionInterface):
    def action(self, dal):
        """
        Delete object from configuration
        """
        self._daq_configuration.destroy_dal(dal)
        return None


class RenameDalAction(ActionInterface):
    def action(self, dal, new_name):
        """
        Rename object in configuration
        """
        dal.rename(new_name)
        return dal


class CopyDalAction(ActionInterface):
    def action(self, dal):
        """
        Copy object in configuration
        """
        self._daq_configuration.add_dal(dal)
        UpdateDalAction(self._daq_configuration)(dal)
        return self._daq_configuration.get_dal(dal.className(), dal.id)


class GetAllClassesAction(ActionInterface):
    """
    Get all classes in the configuration
    """

    def action(self):
        """
        Get all classes in the configuration
        """
        return self._daq_configuration.classes()


class GetAllDalsAction(ActionInterface):
    """
    Get all DALs in the configuration
    """

    def action(self):
        """
        Get all DALs in the configuration
        """
        dals = []
        for class_name in GetAllClassesAction(self._daq_configuration)():
            dals += GetDalsOfClassAction(self._daq_configuration)(class_name)

        return list(set(dals))


class CopyFullConfigurationAction(ActionInterface):
    def action(self, new_file_name):
        """
        Copy full configuration
        """
        CommitConfigurationAction(self._daq_configuration)()
        shutil.copyfile(f"{self._daq_configuration.file_name}", new_file_name)
        return DaqConfigurationWrapper(new_file_name)


class AddDalAction(ActionInterface):
    def action(self, conf_obj_id: str, conf_obj_class: str):
        """
        Add object to configuration
        """
        self._daq_configuration.create_obj(uid=conf_obj_id, class_name=conf_obj_class)
        dal_obj = GetDalObjectAction(self._daq_configuration)(
            conf_obj_id, conf_obj_class
        )
        UpdateDalAction(self._daq_configuration)(dal_obj)
        return dal_obj


class DisableDalAction(ActionInterface):
    def action(self, dal, session_name: str, disable: bool):
        """
        Disable object in configuration
        """
        # Not strictly "nice" but we need to be able to chain things
        session = GetDalObjectAction(self._daq_configuration)(session_name, "Session")
        disabled_objects = getattr(session, "disabled")

        if disable:
            disabled_objects.append(dal)
        elif dal in disabled_objects:
            disabled_objects.remove(dal)

        setattr(session, "disabled", list(set(disabled_objects)))
        return session


# Non-Chainable Actions
class GetDalsOfClassAction(ActionInterface):
    """
    Get list of dals of a certain class
    """

    def action(self, class_id: str):
        return self._daq_configuration.get_dals(class_id)


class GetRelatedDalsAction(ActionInterface):
    """
    Get related dals
    """

    def action(self, dal):
        relations = self._daq_configuration.relations(dal.className())

        relations_list = []
        # Loop over relations
        for rel, rel_info in relations.items():
            rel_val = getattr(dal, rel)
            # Hacky but pybind got fussy about casting list(dal)
            if not isinstance(rel_val, list):
                rel_val = [rel_val]

            relations_list.append(
                {rel: [v for v in rel_val if v is not None], "rel_info": rel_info}
            )

        return relations_list

        CommitConfigurationAction(self._daq_configuration)()


# Tiny bit hacky + hardcoded, lets us disable stuff
class CanBeDisableAction(GetDalObjectAction):
    """
    Can a DAL be disabled?
    """

    def action(self, dal):
        return dal in GetDalsOfClassAction(self._daq_configuration)("Component")


class CommitConfigurationAction(ActionInterface):
    """
    Commit configuration
    """

    def action(self, save_message: str = ""):
        self._daq_configuration.commit(save_message)
        return None


# Actions for getting information
class GetAttributeAction(ActionInterface):
    def action(self, dal, attr_name):
        """
        Get the value of an attribute in a DAL object
        """
        return getattr(dal, attr_name)


class GetClassNameAction(ActionInterface):
    def action(self, dal):
        """
        Get name of DAL class
        """
        return dal.className()


class CheckIsDisabledAction(ActionInterface):
    """
    Check if DAL is disabled
    """

    def action(self, dal, session_name) -> bool:
        session_dal = GetDalObjectAction(self._daq_configuration)(
            session_name, "Session"
        )

        attr_getter = GetAttributeAction(self._daq_configuration)
        disabled_items = attr_getter(session_dal, "disabled")

        return dal in disabled_items

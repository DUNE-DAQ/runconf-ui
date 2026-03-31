"""
Exceptions
"""


# Generic runconf ui exception
class _RunconfUIException(Exception):
    """Base exception class for all runconf-ui exceptions."""

    ...


# ------- State Ops -------- #
# Set of exceptions for state operations
# Generic bad state exception, shouldn't be called
class _RunConfUITreeException(_RunconfUIException):
    """Base exception for tree state operation errors."""

    ...


# DAL is incompatible for a given property
class IncompatibleDalException(_RunConfUITreeException):
    """Raised when a DAL is incompatible for the given property."""

    ...


# Generic attribute exception
class _RunconfUIAttributeException(_RunConfUITreeException):
    """Base exception for attribute-related errors."""

    ...


# Attribute is missing
class AttributeMissingException(_RunconfUIAttributeException):
    """Raised when a required attribute is missing."""

    ...


# Attribute value is wrong
class AttributeValueException(_RunconfUIAttributeException):
    """Raised when an attribute has an invalid value."""

    ...


# ------- Repo Management -------- #
# Set of exceptions for repo management
class _RunConfUIRepoException(_RunconfUIException):
    """Base exception for repository management errors."""

    ...


# When you select a bad DAQ version
class DaqVersionException(_RunConfUIRepoException):
    """Raised when an invalid DAQ version is selected."""

    ...


# When you find a repo with no settings
class MissingRunconfUIConfigException(_RunConfUIRepoException):
    """Raised when a repository has no runconf-ui configuration."""

    ...


# When the user doesn't set runconf-tools repo
class RunConfToolsRepoException(_RunConfUIRepoException):
    """Raised when the runconf-tools repository is not properly configured."""

    ...


# When the config doesn't exist
class ConfigNotFoundInRepoException(_RunConfUIRepoException):
    """Raised when the requested configuration is not found in the repository."""

    ...


# When there is no session
class ConfigBrokenInRepoException(_RunConfUIRepoException):
    """Raised when the configuration in the repository is broken or corrupted."""

    ...


# ------- Configuration Errors -------- #
class _DaqConfigException(_RunconfUIException):
    """Base exception for DAQ configuration errors."""

    ...


# Error when reading config
class ConfigReadException(_DaqConfigException):
    """Raised when an error occurs while reading a configuration."""

    ...


# Error when writing to config
class ConfigWriteException(_DaqConfigException):
    """Raised when an error occurs while writing to a configuration."""

    ...


# When runconf-tools repos aren't linked


# ------ Lookup exceptions -------- #
class _NodeException(_RunconfUIException):
    """Base exception for node lookup errors."""

    ...


class NodeNotFound(_NodeException):
    """Raised when a requested node is not found in the tree."""

    ...


class NodeNotToggleAble(_NodeException):
    """Raised when attempting to toggle a node that is not toggleable."""

    ...


class LoggerNotFound(_RunconfUIException):
    """Raised when a requested logger is not found."""

    ...

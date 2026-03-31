System Configuration
======================
For details on how to write the system configuration YAML file, see `System Configuration <../general/system_configuration.html>`_.

The system configuration module is responsible for parsing the YAML file and providing the relevant information to the rest of the application.
The configuration is processe into an `AssembledConfig` object.

Assembled Dataclasses
----------------------
The assembled dataclasses are the dataclasses that are used by the rest of the application. 

.. autoclass:: runconf_ui.system_configuration.config_reader.AssembledSystem
   :members:

.. autoclass:: runconf_ui.system_configuration.config_reader.AssembledGroup
   :members:

.. autoclass:: runconf_ui.system_configuration.config_reader.AssembledConfig
   :members:

System Configuration Reader
---------------------------
This system config reader reads in the YAML and then processes a given OKS configuration + session into `AssembledConfig` objects which are used by the rest of the application.

.. autoclass:: runconf_ui.system_configuration.config_reader.SystemConfigReader   
   :members:

.. autoclass:: runconf_ui.system_configuration.config_reader.ConfigAssembler   
   :members:

Configuration Builders
------------------------
The builders are responsible for taking the raw YAML and building the `AssembledConfig` objects. This is where the main logic of how the YAML is processed lives.

.. automodule:: runconf_ui.system_configuration.builders
    :members:

Factory Methods
------------------------
The factory methods are responsible for taking the raw YAML and building the `AssembledConfig`

.. automodule:: runconf_ui.system_configuration.factories
   :members:

Internal Dataclassses
------------------------
The internal dataclasses are the dataclasses that are used internally by the system configuration module to process the YAML file. These are not used by the rest of the application.
.. automodule:: runconf_ui.system_configuration.dataclasses
   :members:
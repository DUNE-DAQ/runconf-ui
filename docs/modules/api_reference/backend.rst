Backend Layer
====================

Runconf-UI backend acts as an "API" layer that serves the frontend with necessary data and handles business logic. 

.. note::
    Right now it's not a "true" API layer, as it directly interacts with the database. In the future, we plan to refactor it to be more modular and decoupled from the database.

Context
--------
The necessary information required to boot runconf-ui

.. autoclass:: runconf_ui.backend.runconf_ui_backend.RunconfContext
   :members:


Runconf-UI Backend
--------------------
.. autoclass:: runconf_ui.backend.runconf_ui_backend.RunconfUIBackend
   :members:
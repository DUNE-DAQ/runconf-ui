Repo Manager
================

There are two `repo-managers` available in `runconf`:
- `LocalRepoManager`: Manages repositories that are stored locally on the filesystem.
- `GitRepoManager`: Manages repositories that are stored in a Git repository via `runconftools <https://github.com/DUNE-DAQ/runconftools/tree/develop>`_

Both inherit from the interface `RepoManagerInterface` and implement the necessary methods to manage repositories.

Local Repo Manager
-------------------
.. autoclass:: runconf_ui.repo_manager.LocalRepoManager
   :members:

Remote Repo Manager
---------------------
.. autoclass:: runconf_ui.repo_manager.RemoteRepoManager
   :members:

Interface
----------------
.. autoclass:: runconf_ui.repo_manager.RepoManagerInterface
   :members:
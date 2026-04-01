Quick Start
=============
To get started with runconf-ui, you can follow the instructions in the :doc:`Installation Guide <installation_guide>` to set up the environment and install the necessary dependencies. 
Once you have runconf-ui installed, you can launch the application and start exploring its features.

Command Line Interface
-----------------------
Runconf-UI can be booted through the command line with

.. code:: bash

    runconf-shifter-ui

Additionally we provide scripts to replicate the environment required for various detectors. This can be setup with

.. code:: bash

    source runconf_<YOUR DETECTOR NAME>_env_setup.sh

the currently provided detectors of 
* `np02`
* `np04`

The app can booted either in local mode (`-l`) or remote mode. Booting in remote mode requires the ops + base repositories to be
provided as well as the name of the configuration file (containing a Session) you wish to use.

Using the App
---------------

Opening a Config
~~~~~~~~~~~~~~~~~

Once loaded the application will look like this:

.. image:: ../../_static/editor_open.png
   :alt: The editor with no config loaded


The first step is to select your daq version using the drop down menu

.. image:: ../../_static/version_select.png
   :alt: The editor with version select pressed


Once selected, the Session select will become enabled allowing you to select a session

.. image:: ../../_static/session_select.png
   :alt: The editor with session select pressed


Once the session is selected, a small loading bar will appear whilst the display is set up and the backend generates the
configuration tree.

You should now have a view that looks like


.. image:: ../../_static/editor_ready.png
   :alt: The editor with a config loaded


Modifying a Config
~~~~~~~~~~~~~~~~~~~~
The steps to modifying a config are very simple

1. In the enable/disable panels turn on/off what you want enabled disabled
2. In the adjustable element panels adjust the values of things you want to adjust

Once these are done simply press "create run configuration" and then "save and quit". This will print out the DRUNC
command to run the config.

The diagrams give a visual overview of the user interface:

.. image:: ../../_static/simple_labels.png
   :alt: Basic overview

Firstly, the above image shows the primary methods for interfacing with the interface:

* The file select can be used to open another config.
* The enable/disable buttons can be pressed to enable/disable items in the configuration. The tabs group together different parts of the detector.
* The options panel:

   * Create/Quit both give the option to save and quit
   * Reset resets the configuration to its initial state
   * Help brings up a small help box

The large cental panel contains a few useful features. Firstly, the configuration map/tree view, highlighted below, shows
the full configuration and all enabled/disabled elements. It can be accessed by pressing the `Configuration` tab

.. image:: ../../_static/config_tree.png
   :alt: highlighted config tree

Next, the `System Maps` tab displays the enable/disable states for each panel as well as how each button is related.
For example, here we see that the `TPC` button is controlled by `CRP4`, `CRP5` and `TDE`.

.. image:: ../../_static/system_map_view.png
   :alt: highlighted config tree

Finally, "adjustable elements" (trigger rates etc.) can be accessed via the adjustable tab.

.. image:: ../../_static/adjustable_elements.png
   :alt: highlighted adjustable tab

.. note:: If the object containing an adjustable element is disabled, you will not be able to modify it in this menu.
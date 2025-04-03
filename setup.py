from setuptools import setup

# Determine the install_requires list based on whether config-management is installed
setup(
    name="runconf_ui",
    install_requires=[
    "textual",
    "textual_dev",
    "rich",
],
    extras_require={"develop": ["ipdb", "ipython"],
                    "separate_conf": ["config_management @ git+https://gitlab.cern.ch/dune-daq/online/config-management.git"]},
    package_data={"": ["*.tcss", "*.yml"]},
)
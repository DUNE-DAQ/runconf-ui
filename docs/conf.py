import os
import sys
from importlib.metadata import version as get_version

sys.path.insert(0, os.path.abspath("../src"))
sys.path.insert(0, os.path.abspath("../tests"))

project = "runconf_ui"
author = "Henry Wallace"
release = get_version("runconf_ui")
version = release

html_theme_options = {
    "sidebar_hide_name": True,
    "source_repository": "https://github.com/DUNE-DAQ/runconf-ui",
    "source_branch": "main",
    "source_directory": "docs/",
}


extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
    "sphinx_click",
    "sphinx.ext.mathjax",
]
# Suppress warnings from third-party packages

sphinx_click_mock_imports = ["runconf_ui"]

html_theme = "furo"

# Stop autodoc shortening things aggressively
keep_warnings = False
nitpicky = False

# Ensure paragraphs render correctly in docstrings
trim_docstring_whitespace = True  # removes leading whitespace uniformly

# Napoleon — Sphinx-style docstrings
napoleon_google_docstring = False
napoleon_numpy_docstring = False
napoleon_use_sphinx_docstring = True

# Autodoc
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_typehints_format = "short"
add_module_names = False

autodoc_default_options = {
    "imported-members": False,
}
autodoc_type_aliases = {
    "Style": "rich.style.Style",
}


def autodoc_skip_member(app, what, name, obj, skip, options):
    """Skip members not defined in runconf_ui."""
    module = getattr(obj, "__module__", "") or ""
    if module and not module.startswith("runconf_ui"):
        return True
    return skip


def setup(app):
    app.connect("autodoc-skip-member", autodoc_skip_member)

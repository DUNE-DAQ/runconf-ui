"""
RunconfUIBackend with the repository/conffwk parts replaced, used to exercise
the gRPC layer without a real configuration repository.

Everything about node state (indexing, toggling, setting values, building and
rendering trees) runs through the real backend, state-tree and rendering code;
only versions/sessions, loading and saving, and the DAL config tree are faked.
"""

import logging
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

from runconf_ui.backend import RunconfUIBackend
from runconf_ui.exceptions import LoggerNotFound
from runconf_ui.state_tree import Group, Leaf, State
from runconf_ui.system_configuration.config_reader import (
    AssembledConfig,
    AssembledGroup,
    AssembledSystem,
)
from runconf_ui.utils import get_logger, init_logger
from runconf_ui.utils.rendering import DrawItem, render_config_tree

CONFIG_FILE = "/confs/np02.data.xml"
WORKING_FILE = "/tmp/work/np02.data.xml"
SESSION_NAME = "np02-session"


class MemoryAdapter:
    """In-memory stand-in for a conffwk attribute adapter."""

    def __init__(self, value, dal_included=True):
        self.value = value
        self._dal_included = dal_included

    def get(self):
        return self.value

    def set(self, value):
        self.value = value

    def dal_included(self):
        return self._dal_included


def build_assembled() -> AssembledConfig:
    """Toggles group 'det' (with a tree view) and adjustable group 'triggers'."""
    det = Group("np02")
    crp4 = det.at("crp4")
    crp4.add(Leaf(MemoryAdapter(True), "apa1", "APA 1"))
    crp4.add(Leaf(MemoryAdapter(True), "apa2"))
    # An unlabelled group: flattened in trees, its child is indexed by label only
    hidden = Group("")
    hidden.add(Leaf(MemoryAdapter(True), "pds"))
    det.add(hidden)
    # Excluded at the DAL level -> PARENT_EXCLUDED
    det.at("crp5").add(Leaf(MemoryAdapter(True, dal_included=False), "apa3"))

    trig = Group("trig")
    trig.at("crp4").add(
        Leaf(MemoryAdapter(10), "thresh", "Threshold"), votes=False, propagate=False
    )

    return AssembledConfig(
        excludable=[
            AssembledGroup(
                "det", "Detector", [AssembledSystem(det, False)], view_panel="Det map"
            )
        ],
        adjustable=[
            AssembledGroup("triggers", "Triggers", [AssembledSystem(trig, False)])
        ],
    )


class FakeConfigTreeRenderer:
    items: ClassVar[list[DrawItem]] = [
        DrawItem(
            "segment",
            children=[
                DrawItem("root-seg@Segment", State.INCLUDED),
                DrawItem(
                    "applications",
                    children=[DrawItem("ru-01@ReadoutApplication", State.EXCLUDED)],
                ),
            ],
        )
    ]

    def config_tree_items(self):
        return self.items

    def draw_config_tree(self):
        return render_config_tree(SESSION_NAME, self.items)


class FakeBackend(RunconfUIBackend):
    instances: ClassVar[list["FakeBackend"]] = []

    def __init__(self, ctx):  # deliberately skips RunconfUIBackend.__init__
        self.ctx = ctx
        self.apparatus = ctx.apparatus
        # The real constructor creates the global logger that the state tree uses
        try:
            get_logger()
        except LoggerNotFound:
            init_logger(Path(tempfile.gettempdir()) / "runconf-ui-fake-backend.log")
        self._logger = logging.getLogger("fake-backend")
        self._assembled = None
        self._tree_views = {}
        self.configuration = None
        self.config_session = None
        self.config_tree_renderer = None
        self.config_info = None
        self.info_text = "No Config Selected"
        self.final_save_dir = Path("/out")
        self._save_path = Path("/out/cfg.data.xml")
        self.saved = False
        self.version = None
        self.session = None
        FakeBackend.instances.append(self)

    # versions / sessions
    def get_daq_versions(self):
        return ["v1", "v2"]

    def get_default_version(self):
        return "v2"

    def get_current_version(self):
        return self.version

    def get_sessions(self):
        # Local repos hand out Paths; make sure those survive the round trip.
        return [Path(CONFIG_FILE)] if self.version else []

    def get_current_session(self):
        return self.session

    def set_daq_version(self, version):
        self.version = version

    def set_daq_session(self, session):
        self.session = session

    # lifecycle
    def open_selected_session(self):
        if self.session is None:
            raise ValueError("No session selected!")
        self.configuration = SimpleNamespace(active_database=WORKING_FILE)
        self.config_session = SimpleNamespace(id=SESSION_NAME)
        self.config_tree_renderer = FakeConfigTreeRenderer()
        self._assembled = build_assembled()
        self._update_info_text(Path(CONFIG_FILE))
        self._rebuild_indexes()

    def save_config(self):
        self.saved = True

    # helpers for assertions
    def leaf(self, group, node_id):
        return self._resolve(group, node_id).node

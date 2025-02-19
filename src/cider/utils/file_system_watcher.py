from watchdog.events import FileSystemEventHandler


class FileSystemWatcher(FileSystemEventHandler):
    """Watches a directory for file changes and updates the FileIOPanel instance."""

    def __init__(self, panel):
        self.panel = panel

    def on_any_event(self, event):
        """Trigger refresh when a file is created, deleted, or modified."""
        self.panel.refresh_file_list()

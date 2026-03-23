"""
Main app for runconf-ui
"""

from pathlib import Path

import click

from runconf_ui import RunconfContext, RunconfUIApp
from runconf_ui.utils import LogLevels
 
@click.command()
@click.option('-c', '--config-directory', type=click.Path(), help='Path to your local config directory. This should contain your configs.', envvar="CONFIG_DIR")
@click.option('-o', '--output-directory', type=click.Path(), default=Path('shifter-configs'), show_default=True, help='Directory to save run configs to.')
@click.option('-l', '--use-local', is_flag=True, default=False)
@click.option('-a', '--apparatus', required=True, help='DAQ apparatus to use (e.g. NP02, NP04).', envvar="APPARATUS")
@click.option('-f', '--config-file-name', required=True, help='Config file to find in the ops repo (e.g. <X>.data.xml).', envvar="SESSION_FILE")
@click.option('-b', '--base-url', required=True, help='URL for the BASE repository.', envvar="BASE_URL")
@click.option('-r', '--ops-url', required=True, help='URL for the operations repository.', envvar="OPERATION_URL")
@click.option('-d', '--log-level', default='INFO', show_default=True, help='Debug level (INFO, WARNING, DEBUG)')
def cli(apparatus: str, config_directory: str, output_directory: str, use_local: bool, config_file_name: str, base_url: str, ops_url: str, log_level: LogLevels="INFO"):
    """runconf-ui — run configuration interface."""
    context = RunconfContext(
        apparatus=apparatus,
        conf_directory=Path(config_directory),
        use_local=use_local,
        config_file_name=config_file_name,
        base_url=base_url,
        ops_url=ops_url,
        output_directory=Path(output_directory),
        log_level=log_level,
    )
    print(RunconfUIApp(context).run())

if __name__ == '__main__':
    context = RunconfContext(
        apparatus="dummy",
        conf_directory=Path("/tmp/pytest-of-hwallace/pytest-current/configscurrent"),
        use_local=True,
        output_directory=Path("test-cfg"),
        log_level="INFO",
    )
        
    RunconfUIApp(context).run()

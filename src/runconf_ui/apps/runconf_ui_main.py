"""
Main app for runconf-ui
"""

from pathlib import Path

import click

from runconf_ui import RunconfContext, RunconfUIApp
from runconf_ui.utils.logging import LogLevels

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

_shared_options = [
    click.option('-a', '--apparatus', required=True, help='DAQ apparatus to use (e.g. NP02, NP04).'),
    click.option('-o', '--output-directory', type=click.Path(), default='shifter-configs', show_default=True, help='Directory to save run configs to.'),
    click.option('-l', '--log-level', default='INFO', show_default=True, help='Debug level (INFO, WARNING, DEBUG)'),

]

_config_dir_local = click.option('-c', '--config-directory', type=click.Path(), required=True, help='Path to your local config directory. This should contain your configs.')
_config_dir_remote = click.option('-c', '--config-directory', type=click.Path(), required=True, help='Path to pull remote configs into. runconf-tools will pull the remote repository here.')

def shared_options(func):
    for option in reversed(_shared_options):
        func = option(func)
    return func


@click.group(context_settings=CONTEXT_SETTINGS)
def cli():
    """runconf-ui — run configuration interface."""
    pass


@cli.command(short_help='Open runconf-ui using a local directory.')
@shared_options
@_config_dir_local
def run_local(apparatus: str, config_directory: str, output_directory: str, log_level: LogLevels="INFO"):
    """Launch runconf-ui against a local config directory."""
    context = RunconfContext(
        apparatus=apparatus,
        conf_directory=Path(config_directory),
        use_local=True,
        output_directory=Path(output_directory),
        log_level=log_level,
    )
    print(RunconfUIApp(context).run())


@cli.command(short_help='Open runconf-ui against the remote repository.')
@shared_options
@_config_dir_remote
@click.option('-f', '--config-file-name', required=True, help='Config file to find in the ops repo (e.g. <X>.data.xml).')
@click.option('-b', '--base-url', required=True, help='URL for the BASE repository.')
@click.option('-r', '--ops-url', required=True, help='URL for the operations repository.')
def run(apparatus: str, config_directory: str, output_directory: str, config_file_name: str, base_url: str, ops_url: str, log_level: LogLevels="INFO"):
    """Launch runconf-ui against a remote repository."""
    context = RunconfContext(
        apparatus=apparatus,
        conf_directory=Path(config_directory),
        use_local=False,
        config_file_name=config_file_name,
        base_url=base_url,
        ops_url=ops_url,
        output_directory=Path(output_directory),
        log_level=log_level,
    )
    print(RunconfUIApp(context).run())


def main():
    cli()


if __name__ == '__main__':
    context = RunconfContext(
        apparatus="dummy",
        conf_directory=Path("/tmp/pytest-of-hwallace/pytest-current/configscurrent"),
        use_local=True,
        output_directory=Path("test-cfg"),
        log_level="INFO",
    )
        
    RunconfUIApp(context).run()

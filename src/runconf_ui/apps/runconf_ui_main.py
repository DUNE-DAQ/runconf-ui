"""
Main app for runconf-ui
"""

import os
from pathlib import Path

import click

from runconf_ui import RunconfContext, RunconfUIApp, RunconfUIBackend
from runconf_ui.utils import LogLevels


def get_exit_msg(backend: RunconfUIBackend) -> str:
    """Generate exit message with drunc command for run-control launch.

    Quick message to return shortcut for run-control that can be sourced
    as a shell script to launch the next DAQ run.

    :param backend: RunconfUIBackend instance to grab config info from
    :returns: Command string to run in terminal to launch run-control, or error message
    :rtype: str
    """
    # We'll grab the environment variables
    run_mode = Path(os.getenv("PROCESS_MANAGER_CONFIG", "ssh-standalone")).stem
    buffer_id = os.getenv("SESSION_NAME", os.getlogin())
    if backend.config_session is None:
        return "No session selected, cannot use DRUNC"

    config_file = backend.config_save_path

    if not config_file.is_file():
        return f"Config file {config_file} not created, cannot use DRUNC"

    config_session = getattr(backend.config_session, "id")

    run_cmd = (
        f"drunc-unified-shell {run_mode} {config_file} {config_session} {buffer_id}"
    )

    output_script = f"/tmp/shifter_configs-{buffer_id}/set_next_run.sh"
    with open(f"{output_script}", "w") as f:
        f.write(f"export EHN1_RUN_FILE={Path(config_file).expanduser()}\n")
        f.write(f"export EHN1_RUN_CONFIG_ID={config_session}\n")
        f.write(f"export EHN1_RUN_COMMAND='{run_cmd}'\n")

    return os.getenv("EHN1_RC_LAUNCH", run_cmd)

# HW Again a bit hacky, but cleaner than defining in the CLI itself!
DEFAULT_CONFIG_EXTENSION = f"-{os.getenv('SESSION_NAME')}" if os.getenv("SESSION_NAME") else ""
DEFAULT_CONFIG_PATH = Path().cwd()/f"config{DEFAULT_CONFIG_EXTENSION}"
    
@click.command()
@click.option(
    "-c",
    "--config-directory",
    type=click.Path(),
    help="Path to your local config directory. This should contain your configs. Can be read from the CONFIG_DIR environment variable.",
    envvar="CONFIG_DIR",
    default=DEFAULT_CONFIG_PATH
)
@click.option(
    "-a",
    "--apparatus",
    required=True,
    help="DAQ apparatus to use (e.g. NP02, NP04). Can be read from the APPARATUS environment variable.",
    envvar="APPARATUS",
)
@click.option(
    "-o",
    "--output-directory",
    type=click.Path(),
    default=Path("shifter-configs"),
    show_default=True,
    help="Directory to save run configs to.",
)
@click.option(
    "-l",
    "--use-local",
    is_flag=True,
    default=False,
    help="Use a local filesystem to get you OKS config.",
)
@click.option(
    "-f",
    "--config-file-name",
    help="Config file to find in the ops repo (e.g. <X>.data.xml). Can be read from the SESSION_FILE environment variable.",
    envvar="SESSION_FILE",
)
@click.option(
    "-b",
    "--base-url",
    default="ssh://git@gitlab.cern.ch:7999/dune-daq/online/ehn1-daqconfigs.git",
    help="URL for the BASE repository. Can be read from the BASE_URL environment variable.",
    envvar="BASE_URL",
)
@click.option(
    "-r",
    "--ops-url",
    help="URL for the operations repository. Can be read from the OPERATION_URL environment variable.",
    envvar="OPERATION_URL",
)
@click.option(
    "-d",
    "--log-level",
    default="INFO",
    show_default=True,
    help="Debug level (INFO, WARNING, DEBUG)",
)
def cli(
    apparatus: str,
    config_directory: str,
    output_directory: str,
    use_local: bool,
    config_file_name: str,
    base_url: str,
    ops_url: str,
    log_level: LogLevels = "INFO",
):
    """CLI interface for runconf-ui.

    Launches the interactive configuration UI and saves selected configurations
    to the specified output directory. Invoked with the runconf-shifter-ui command.

    :param apparatus: DAQ apparatus name (e.g., NP02, NP04)
    :param config_directory: Path to configuration directory
    :param output_directory: Directory to save run configs to
    :param use_local: Use local filesystem instead of remote API
    :param config_file_name: Config file to find in the ops repo
    :param base_url: URL for the BASE repository
    :param ops_url: URL for the operations repository
    :param log_level: Log level (INFO, WARNING, DEBUG)
    """
    ctx = RunconfContext(
        apparatus=apparatus,
        conf_directory=Path(config_directory),
        use_local=use_local,
        config_file_name=config_file_name,
        base_url=base_url,
        ops_url=ops_url,
        output_directory=Path(output_directory),
        log_level=log_level,
    )

    backend = RunconfUIBackend(ctx)
    RunconfUIApp(backend).run()
    print(get_exit_msg(backend))

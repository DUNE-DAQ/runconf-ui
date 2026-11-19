"""
Main app for runconf-ui
"""

import os
import re
import shutil
from pathlib import Path
from typing import TypedDict

import click

from runconf_ui import RepoManagerType, RunconfContext, RunconfUIApp, RunconfUIBackend
from runconf_ui.utils import LogLevels
from runconf_ui.api.grpc_service import run_until_quit


class ApparatusDefaults(TypedDict):
    base_url: str
    ops_url: str
    config_file_name: str
    config_dir: str


def get_apparatus_defaults(apparatus: str) -> ApparatusDefaults:
    """Dynamically finds and parses the installed environment setup shell script
    for a given apparatus to extract configuration defaults.
    """
    app_lower = apparatus.lower()
    script_name = f"runconf_{app_lower}_env_setup.sh"

    # Locate where the script was installed in the current environment's PATH
    script_path = shutil.which(script_name)

    if not script_path:
        raise click.UsageError(
            f"Could not find setup script '{script_name}'. "
            f"Please add '{script_name}' to runconf-ui/scripts and to the pyproject.toml"
        )

    defaults: dict[str, str] = {}

    # Matches lines like: export KEY="VALUE" or export KEY=${OTHER_VAR}/value
    # Specifically captures the key and everything inside the quotes
    export_pattern = re.compile(
        r'^\s*export\s+([A-Za-z0-9_]+)\s*=\s*(?:"([^"]*)"'
        r"|'([^']*)'|([^#\s]*))"
    )

    with open(script_path) as f:
        for line in f:
            match = export_pattern.match(line.strip())
            if match:
                key = match.group(1)
                value = next((v for v in match.groups()[1:] if v is not None), "")
                defaults[key] = value

    # Map the environment variable names to your internal TypedDict structure
    # Providing fallbacks in case the script structure shifts slightly
    mapped_defaults: ApparatusDefaults = {
        "base_url": defaults.get("BASE_URL", ""),
        "ops_url": defaults.get("OPERATION_URL", ""),
        "config_file_name": defaults.get("SESSION_FILE", ""),
        "config_dir": defaults.get("CONFIG_DIR", ""),
    }

    # Evaluate simple string interpolations if necessary (like ${DBT_AREA_ROOT})
    if "${DBT_AREA_ROOT}" in mapped_defaults["config_dir"]:
        dbt_root = os.getenv("DBT_AREA_ROOT", "")
        mapped_defaults["config_dir"] = mapped_defaults["config_dir"].replace(
            "${DBT_AREA_ROOT}", dbt_root
        )

    # Sanity check to make sure we actually extracted meaningful data
    if not any(mapped_defaults.values()):
        raise ValueError(
            f"Script '{script_name}' was found but yielded no default variables."
        )

    return mapped_defaults


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

    config_file = backend.final_save_path.resolve()

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


def context_options(func):
    """Click options describing the RunconfContext (shared by the TUI and the server)."""
    options = [
        click.option(
            "-c",
            "--config-directory",
            type=click.Path(),
            help="Path to your local config directory. This should contain your configs. Can be read from the CONFIG_DIR environment variable.",
            envvar="CONFIG_DIR",
            default=Path("base-configs"),
        ),
        click.option(
            "-a",
            "--apparatus",
            help="DAQ apparatus to use (e.g. NP02, NP04, NP02_EMU). Can be read from the APPARATUS environment variable.",
            envvar="APPARATUS",
        ),
        click.option(
            "-o",
            "--output-directory",
            type=click.Path(),
            default=Path("shifter-configs"),
            show_default=True,
            help="Directory to save run configs to.",
        ),
        click.option(
            "-t",
            "--repo-type",
            type=click.Choice(RepoManagerType.values()),
            default="remote",
            help="Type of repository to use (local or remote). Emulation is selected via --apparatus, not here.",
        ),
        click.option(
            "-f",
            "--config-file-name",
            help="Config file to find in the ops repo (e.g. <X>.data.xml). Can be read from the SESSION_FILE environment variable.",
            envvar="SESSION_FILE",
        ),
        click.option(
            "-b",
            "--base-url",
            help="URL for the BASE repository. Can be read from the BASE_URL environment variable.",
            envvar="BASE_URL",
        ),
        click.option(
            "-r",
            "--ops-url",
            help="URL for the operations repository. Can be read from the OPERATION_URL environment variable.",
            envvar="OPERATION_URL",
        ),
        click.option(
            "-d",
            "--log-level",
            default="INFO",
            show_default=True,
            help="Debug level (INFO, WARNING, DEBUG)",
        ),
    ]
    for option in reversed(options):
        func = option(func)
    return func


def build_context(
    apparatus: str | None,
    config_directory: str,
    output_directory: str,
    repo_type: str,
    config_file_name: str | None,
    base_url: str | None,
    ops_url: str | None,
    log_level: LogLevels = "INFO",
) -> RunconfContext:
    """Turn the context options into a RunconfContext, filling apparatus defaults.

    :raises click.UsageError: apparatus missing, or remote URLs only partly given
    """
    if apparatus is None:
        raise click.UsageError(
            "Apparatus must be specified with -a or APPARATUS env variable"
        )

    repo_type_enum = RepoManagerType.from_string(repo_type)

    # When we JUST provide the apparatus
    if repo_type_enum != RepoManagerType.LOCAL:
        apparatus_vars = (base_url, ops_url, config_file_name)
        if all(v is None for v in apparatus_vars):
            apparatus_defaults = get_apparatus_defaults(apparatus)
            base_url = apparatus_defaults.get("base_url")
            ops_url = apparatus_defaults.get("ops_url")
            config_file_name = apparatus_defaults.get("config_file_name")
            config_directory = apparatus_defaults.get("config_dir")
        elif any(v is None for v in apparatus_vars):
            raise click.UsageError(
                "Specify all of --base-url, --ops-url, and --config-file-name together, or omit all three to use apparatus defaults."
            )

    return RunconfContext(
        apparatus=apparatus,
        conf_directory=Path(config_directory),
        repo_type=repo_type_enum,
        config_file_name=config_file_name,
        base_url=base_url,
        ops_url=ops_url,
        output_directory=Path(output_directory),
        log_level=log_level,
    )


@click.command()
@context_options
@click.option(
    "-g",
    "--grpc-address",
    default=None,
    help="Talk to the backend over gRPC. Either host:port of a running "
    "runconf-ui-server (which owns the context, so the options above are ignored), "
    "or 'local' to start one in this process. Omit to use the backend directly. "
    "Can be read from RUNCONF_GRPC_ADDRESS.",
    envvar="RUNCONF_GRPC_ADDRESS",
)
def cli(grpc_address: str | None = None, **context_args):
    """
    Launches the interactive configuration UI and saves selected configurations
    to the specified output directory. Invoked with the runconf-shifter-ui command.

    \f

    :param grpc_address: host:port of a runconf-ui-server, 'local', or None
    :param context_args: the context options (see ``context_options``)
    """
    if grpc_address is None:
        backend = RunconfUIBackend(build_context(**context_args))
        RunconfUIApp(backend).run()
        print(get_exit_msg(backend))
        return

    _run_over_grpc(grpc_address, **context_args)


def _run_over_grpc(address: str, **context_args) -> None:
    """Run the TUI against a RunconfService instead of an in-process backend."""
    # Imported here so the plain TUI doesn't need grpc/runconfschema installed
    from runconf_ui.api.grpc_client import RpcBackend
    from runconf_ui.api.grpc_service import serve

    server = None
    if address == "local":
        # The server shares this process with the TUI: keep its logs off the terminal
        server, _, port = serve(
            "127.0.0.1:0", build_context(**context_args), log_to_terminal=False
        )
        address = f"127.0.0.1:{port}"

    backend = RpcBackend(
        address,
        log_dir=Path(context_args["output_directory"]),
        log_level=context_args["log_level"],
    )
    try:
        RunconfUIApp(backend).run()  # type: ignore[arg-type]
        print(get_exit_msg(backend))  # type: ignore[arg-type]
    finally:
        backend.close()
        if server is not None:
            server.stop(1).wait()


@click.command()
@click.option(
    "-g",
    "--grpc-address",
    default="[::]:50051",
    show_default=True,
    help="Address to listen on. Can be read from RUNCONF_GRPC_ADDRESS.",
    envvar="RUNCONF_GRPC_ADDRESS",
)
@context_options
def server_cli(grpc_address: str, **context_args):
    """Run the runconf-ui gRPC backend until a client sends QUIT or CREATE_QUIT.

    With --apparatus (or APPARATUS) the server boots itself with that context.
    Without it, the server waits for a single boot RPC from whoever launched it.
    Frontends then connect with ``runconf-shifter-ui --grpc-address <host:port>``.
    """
    context = None
    if context_args["apparatus"] is not None:
        context = build_context(**context_args)
        print(f"Booted runconf-ui server for {context.apparatus} on {grpc_address}", flush=True)
    else:
        print(f"runconf-ui server on {grpc_address}: waiting for a boot request", flush=True)

    run_until_quit(grpc_address, context)


if __name__ == "__main__":
    # FOR TESTING ONLY
    ctx_ = RunconfContext(
        apparatus="dummy",
        conf_directory=Path("/tmp/pytest-of-hwallace/pytest-current/configscurrent"),
        repo_type=RepoManagerType.LOCAL,
        output_directory=Path("test-cfg"),
        log_level="INFO",
    )
    backend_ = RunconfUIBackend(ctx_)

    RunconfUIApp(backend_).run()

    print(get_exit_msg(backend_))

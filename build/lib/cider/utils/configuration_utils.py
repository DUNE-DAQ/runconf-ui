from rich import print
from cider.interfaces.controller.config_wrapper import ConfigurationWrapper

def print_confobj_enabled(configuration_object):
    return f"[yellow]{getattr(configuration_object, 'id')}[/yellow]@[green]{configuration_object.className()}[/green]"

def print_confobj_disabled(configuration_object):
    return f"[grey]{getattr(configuration_object, 'id')}[/grey]@[grey]{configuration_object.className()}[/grey] [bold red]DISABLED[/bold red]"

def print_conf_tree(config_wrapper: ConfigurationWrapper, depth: int | None = None):
    pass
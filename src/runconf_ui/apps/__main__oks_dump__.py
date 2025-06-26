"""
HW: Recreation of https://github.com/DUNE-DAQ/oks/blob/develop/apps/oks_dump.cxx in python
"""

import oks
import click
from pprint import pprint


@click.command()
@click.argument("file_name", type=click.Path(exists=True))
def main(file_name: str):
    """
    Main function to dump the contents of an OKS file.
    :param file_name: The name of the OKS file to dump.
    """
    # Create an OksKernel instance
    oks_kernel = oks.OksKernel()

    oks_kernel.set_test_duplicated_objects_via_inheritance_mode(True)
    oks_kernel.load_file(str(file_name))

    for i in oks_kernel.schema_files():
        print(f"Schema file: {i}")

    for i in oks_kernel.data_files():
        print(f"Data file: {i}")

    pprint(oks_kernel.classes()["ResourceSetAND"].all_sub_classes())

    print("OKS file loaded successfully.")

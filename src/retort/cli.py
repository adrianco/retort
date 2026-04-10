"""Retort CLI entry point."""

import click

from retort import __version__


@click.group()
@click.version_option(version=__version__, prog_name="retort")
def main() -> None:
    """Retort — Platform Evolution Engine.

    Distill the best from the combinatorial mess.
    """


if __name__ == "__main__":
    main()

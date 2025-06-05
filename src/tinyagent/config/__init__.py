"""
Configuration management for the tinyAgent framework.

This package provides utilities for loading, validating, and accessing
configuration settings from different sources (files, environment variables, etc.).
"""

import shutil
from pathlib import Path

import click

from .config import TinyAgentConfig, get_config_value, load_config

__all__ = [
    "load_config",
    "get_config_value",
    "TinyAgentConfig",
]

"""Configuration initialization module for tinyAgent."""


@click.group()
def cli():
    """Configuration management commands."""
    pass


@cli.command()
@click.option("--force", is_flag=True, help="Overwrite existing config file")
def init(force):
    """Initialize a new config.yml file in the current directory."""
    target = Path("config.yml")

    if target.exists() and not force:
        click.echo("config.yml already exists. Use --force to overwrite.")
        return

    # Get the example config from our package
    example_config = (
        Path(__file__).parent.parent / "observability" / "config" / "example_config.yml"
    )

    if not example_config.exists():
        click.echo("Error: Could not find example config template.")
        return

    # Copy the example config
    shutil.copy(example_config, target)
    click.echo("Created config.yml with default settings.")
    click.echo("Edit this file to configure your tinyAgent instance.")


if __name__ == "__main__":
    cli()

"""Main CLI interface for site-guard."""

import asyncio
from pathlib import Path

import click
from loguru import logger

from site_guard.application.monitoring_app import MonitoringApplication
from site_guard.infrastructure.logging.setup import setup_logging
from site_guard.infrastructure.persistence.config import FileConfigLoader


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to configuration file (YAML or JSON)",
)
@click.option(
    "--interval", "-i", type=int, help="Check interval in seconds (overrides config file setting)"
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option(
    "--log-file",
    type=str,
    help="Application log file (separate from monitoring results log), defaults to 'site_guard.log'",
)
def main(config: Path, interval: int | None, verbose: bool, log_file: str | None) -> None:
    """Site Guard - Monitor website availability and content."""
    setup_logging(verbose, log_file)

    logger.info("Site Guard starting...")

    config_loader = FileConfigLoader()
    app = MonitoringApplication(config_loader=config_loader)

    try:
        asyncio.run(app.run(config, interval))
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
        click.echo("\nMonitoring stopped.")
    except Exception as e:
        logger.exception(f"Application error: {e}")
        logger.error(f"Error: {e}", err=True)
        raise click.Abort() from e


if __name__ == "__main__":
    main()

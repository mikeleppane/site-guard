"""Main CLI interface for site-guard."""

import asyncio
from pathlib import Path

import click
from loguru import logger

from site_guard.application.monitoring_app import MonitoringApplication
from site_guard.domain.models.config import MonitoringConfig
from site_guard.infrastructure.http.checker import HttpSiteChecker
from site_guard.infrastructure.logging.logger import FileLogger
from site_guard.infrastructure.logging.setup import setup_logging
from site_guard.infrastructure.persistence.config import FileConfigLoader


def load_config(config_path: Path) -> MonitoringConfig:
    """Load configuration from the specified path."""
    from loguru import logger

    try:
        return FileConfigLoader().load_config(config_path=config_path)
    except Exception as e:
        logger.error(
            f"Failed to load configuration from {config_path}: {e}.\n\nPlease check your config file."
        )
        raise click.Abort() from e


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
    logger.info("Site Guard starting...")

    setup_logging(verbose)
    app_config = load_config(config)

    app_log_file = "site_guard.log"
    if log_file is not None:
        app_log_file = log_file
    elif app_config.log_file is not None:
        app_log_file = app_config.log_file
    file_logger = FileLogger(log_file_path=app_log_file)

    # Override log file if provided via CLI

    site_checker = HttpSiteChecker()
    app = MonitoringApplication(
        config=app_config,
        io_logger=file_logger,
        site_checker=site_checker,
    )

    try:
        asyncio.run(app.run(interval))
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
        click.echo("\nMonitoring stopped.")
    except Exception as e:
        logger.exception(f"Application error: {e}")
        logger.error(f"Error: {e}", err=True)
        raise click.Abort() from e


if __name__ == "__main__":
    main()

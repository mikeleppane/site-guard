# Site Guard 🛡️

A modern, asynchronous website monitoring tool that helps administrators detect problems on their sites by periodically checking availability and content requirements.

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## 🚀 Features

- **Asynchronous Monitoring**: Efficiently checks multiple sites concurrently using `aiohttp`
- **Content Validation**: Verifies that pages contain required text or elements
- **Flexible Configuration**: YAML/JSON configuration with customizable timeouts and intervals
- **Structured Logging**: Beautiful console output with structured JSON logs using Loguru
- **Error Classification**: Distinguishes between connection errors and content validation failures
- **Performance Metrics**: Measures and reports response times for each check
- **Log Rotation**: Automatic log rotation and compression to manage disk space
- **Type Safety**: Full type annotations with mypy compliance
- **Clean Architecture**: Domain-driven design with clear separation of concerns

## 📋 Requirements

- Python 3.12 or higher
- Internet connection for monitoring external sites

## 🔧 Installation

### From Source

```bash
git clone <repository-url>
cd site-guard
pip install -e .
```

### Development Setup

```bash
git clone <repository-url>
cd site-guard
pip install -e ".[dev]"
pre-commit install
```

## 🚦 Quick Start

1. **Create a configuration file** (`config.yaml`):

```yaml
check_interval: 30  # seconds
log_file: "site_guard.log"
sites:
  - url: "https://example.com"
    content_requirement: "Example Domain"
    timeout: 10
  - url: "https://httpbin.org/json"
    content_requirement: "slideshow"
    timeout: 15
```

2. **Run the monitor**:

```bash
site-guard --config config.yaml
```

3. **Monitor with custom settings**:

```bash
# Override check interval
site-guard --config config.yaml --interval 60

# Enable verbose logging
site-guard --config config.yaml --verbose

# Save application logs to file
site-guard --config config.yaml --log-file app.log
```

## ⚙️ Configuration

### Configuration File Format

Site Guard supports both YAML and JSON configuration files:

```yaml
# Monitoring settings
check_interval: 30        # Check interval in seconds
log_file: "monitoring.log" # Path to monitoring results log

# Sites to monitor
sites:
  - url: "https://www.python.org/"
    content_requirement: "Python"
    timeout: 10
  - url: "https://www.rust-lang.org/"
    content_requirement: "Rust"
    timeout: 15
```

### Configuration Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `check_interval` | integer | Time between monitoring rounds (seconds) | 60 |
| `log_file` | string | Path to monitoring results log file | `site_guard.log` |
| `sites` | array | List of sites to monitor | Required |
| `sites[].url` | string | URL to monitor | Required |
| `sites[].content_requirement` | string | Text that must be present in response | Required |
| `sites[].timeout` | integer | Request timeout in seconds | 30 |

## 📊 Output and Logging

### Console Output

Site Guard provides colorized console output showing the status of each check:

```
2025-06-06 10:30:00 | INFO     | Starting site monitoring with 3 sites
2025-06-06 10:30:00 | INFO     | Check interval: 30 seconds
2025-06-06 10:30:01 | SUCCESS  | ✓ https://example.com - 245ms
2025-06-06 10:30:01 | WARNING  | ✗ https://broken-site.com - connection_error: HTTP 404: Not Found
2025-06-06 10:30:02 | INFO     | Monitoring round completed: 2 successful, 1 failed
```

### Log Files

Monitoring results are saved to structured JSON logs:

```json
{
  "timestamp": "2025-06-06T10:30:01.123456",
  "url": "https://example.com",
  "status": "success",
  "response_time_ms": 245,
  "error_message": null,
  "check_type": "site_monitoring"
}
```

## 🏗️ Architecture

Site Guard follows clean architecture principles with clear separation of concerns:

```
src/site_guard/
├── domain/              # Business logic and rules
│   ├── models/         # Data models (SiteConfig, CheckResult)
│   ├── services/       # Service interfaces
│   └── repositories/   # Repository interfaces
├── application/        # Use cases and orchestration
│   └── monitoring_app.py
└── infrastructure/     # External integrations
    ├── http/          # HTTP client implementation
    ├── persistence/   # Configuration and logging
    └── logging/       # Logging setup
```

## 🧪 Development

### Running Tests

```bash
pytest
pytest --cov=site_guard --cov-report=html
```

### Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check . --fix

# Type checking
mypy src/

# Run all pre-commit hooks
pre-commit run --all-files
```

### Project Structure

The project uses modern Python packaging with:
- **pyproject.toml**: Project configuration and dependencies
- **Ruff**: Fast linting and formatting
- **mypy**: Static type checking
- **pytest**: Testing framework
- **pre-commit**: Git hooks for code quality

## 🔍 Error Types

Site Guard classifies errors into distinct categories:

- **SUCCESS**: Site is accessible and content requirement is met
- **CONNECTION_ERROR**: Network issues, DNS resolution failures, HTTP errors (4xx/5xx)
- **CONTENT_ERROR**: Site is accessible but doesn't contain required content
- **TIMEOUT_ERROR**: Request exceeded the configured timeout

## 📝 Examples

### Basic Monitoring

```bash
site-guard --config sites.yaml
```

### High-Frequency Monitoring

```bash
site-guard --config critical-sites.yaml --interval 10 --verbose
```

### Production Deployment

```bash
site-guard --config production.yaml --log-file /var/log/site-guard/app.log
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting (`pre-commit run --all-files`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [aiohttp](https://docs.aiohttp.org/) for async HTTP requests
- Logging powered by [Loguru](https://loguru.readthedocs.io/)
- CLI interface using [Click](https://click.palletsprojects.com/)
- Configuration validation with [Pydantic](https://docs.pydantic.dev/)

---

**Site Guard** - Keeping your websites healthy, one check at a time! 🏥✨

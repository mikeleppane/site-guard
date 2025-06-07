SRC_DIR = ./src
TEST_DIR = ./tests

.PHONY: check fix run

format:
	uv run ruff format $(SRC_DIR) $(TEST_DIR)
	uv run isort $(SRC_DIR) $(TEST_DIR)

check:
	uv run mypy --version
	uv run mypy $(SRC_DIR) $(TEST_DIR)
	uv run ruff --version
	uv run ruff check $(SRC_DIR) $(TEST_DIR)
	uv run ruff format --check $(SRC_DIR) $(TEST_DIR)
	uv run isort --version
	uv run isort --check-only $(SRC_DIR) $(TEST_DIR)

fix:
	uv run ruff format $(SRC_DIR) $(TEST_DIR)
	uv run isort $(SRC_DIR) $(TEST_DIR)
	uv run ruff check --fix $(SRC_DIR) $(TEST_DIR)

test:
	uv run pytest -v $(TEST_DIR)

test-cov:
	uv run pytest --cov=$(SRC_DIR) --cov-report=term-missing --cov-report=html $(TEST_DIR)

help:
	uv run python src/library_db/app.py --help

show-outdated:
	 uv run pip list --outdated

# Contributing to Shield Orchestrator

Thank you for your interest in contributing to Shield Orchestrator! This project is part of the [Shield Ecosystem](https://github.com/gbvk312).

## Getting Started

1. **Fork & Clone:**
   ```bash
   git clone https://github.com/gbvk312/shield-orchestrator.git
   cd shield-orchestrator
   ```

2. **Install Dependencies:**
   ```bash
   uv sync
   ```

3. **Run Tests:**
   ```bash
   uv run pytest
   ```

## Development Workflow

- Create a feature branch from `master`.
- Ensure all tests pass before submitting a PR.
- Run `uv run ruff check .` and `uv run mypy shield_orchestrator` for linting.
- Follow existing code conventions (type hints, clear docstrings).

## Reporting Issues

- Use the GitHub issue tracker.
- For security vulnerabilities, please email [gbvk.312@gmail.com](mailto:gbvk.312@gmail.com) instead of creating a public issue.

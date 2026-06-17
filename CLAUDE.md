# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

`proceed` is a Python library for executing declarative batch pipelines via Docker containers. Pipelines are defined in YAML and describe sequences of Steps, each mapped to a Docker image and command. The core modules are `src/proceed/model.py` (data models), `src/proceed/docker_runner.py` (execution engine), and `src/proceed/cli.py` (CLI entry point).

## Dev environment setup

Use conda and hatch — not plain pip:

```bash
conda env create -f dev-environment.yml
conda activate proceed-dev
```

Hatch manages the test and docs environments automatically; you don't need to install test dependencies manually.

## Test commands

Most tests require Docker to be installed and the daemon running.

Full suite (requires Docker):
```bash
hatch run test:cov
```

Docker-free subset (faster for model/logic changes):
```bash
hatch run test:cov tests/proceed/test_model.py tests/proceed/test_file_matching.py tests/proceed/test_config_options.py
```

Run a single test by name:
```bash
hatch run test:cov -k "test_name"
```

## Code style

- All public functions must have type annotations.
- All public functions must have docstrings.
- Follow existing patterns in `src/proceed/` — the codebase uses dataclasses for models and keeps YAML serialization logic in `yaml_data.py`.

## Docs

Build Sphinx docs locally:
```bash
hatch run docs:html
```

Clean build artifacts:
```bash
hatch run docs:clean
```

## Release

Releases are tag-driven: pushing a semver tag triggers CI to publish to PyPI and deploy docs to GitHub Pages. Version is sourced from `src/proceed/__about__.py` at build time.

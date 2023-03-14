# This file contains Sphinx-specific configuration for documentation generation.
# General project config, like project name and version, should stay in pyproject.toml.
# We can pass general project values to sphinx-build using the -D command line option.

templates_path=["source/_templates"]
html_static_path=["source/_static"]

html_theme="alabaster"

extensions=[
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
]
autosummary_generate=True
autodoc_typehints = "both"

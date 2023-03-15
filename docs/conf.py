# This file contains Sphinx-specific configuration for documentation generation.
# General project config, like project name and version, should stay in pyproject.toml.
# We can pass general project values to sphinx-build using the -D command line option.

templates_path=["_templates"]
html_static_path=["_static"]

html_theme="pyramid"

extensions=[
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
]
autosummary_generate=True
autodoc_typehints = "description"
autodoc_member_order = 'bysource'

# This file contains Sphinx-specific configuration for documentation generation.
# General project config, like project name and version, should stay in pyproject.toml.
# We can pass general project values to sphinx-build using the -D command line option.

# Unclear why "_templates" is relative to the docs/source/ dir,
# while "source/_static" is relative to the docs/ dir itself.
# But this is what seems to work -- so whatever!
templates_path=["_templates"]
html_static_path=["source/_static"]
html_css_files=["custom.css"]
html_theme="pyramid"

extensions=[
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
]
autosummary_generate=True
autodoc_typehints = "description"
autodoc_member_order = 'bysource'

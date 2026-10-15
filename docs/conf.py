"""Sphinx configuration for the noidea documentation site."""

import tomllib
from pathlib import Path

# Read the version from pyproject.toml so the site can never drift from the released package.
# Read the Docs builds without installing noidea, so package metadata is not available here.
_PYPROJECT_PATH = Path(__file__).resolve().parent.parent / "pyproject.toml"
with _PYPROJECT_PATH.open("rb") as _pyproject_file:
    release = tomllib.load(_pyproject_file)["project"]["version"]
version = release

project = "noidea"
author = "AccursedGalaxy"
copyright = "2026, AccursedGalaxy"

extensions = [
    "myst_parser",
    "sphinx_copybutton",
]

source_suffix = {".md": "markdown"}
root_doc = "index"
# CONVENTION.md is the maintenance contract for docs/, not a page for readers.
exclude_patterns = ["_build", "CONVENTION.md"]

myst_enable_extensions = ["colon_fence", "deflist"]
# Generate anchors for H1 to H3, so pages can link to sections as `page.md#heading`.
myst_heading_anchors = 3

# Copy only the command from a block, never a pasted prompt or output.
copybutton_exclude = ".linenos, .gp, .go"

html_theme = "furo"
html_title = f"noidea {release}"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_theme_options = {
    "light_css_variables": {
        "color-brand-primary": "#1f6feb",
        "color-brand-content": "#1f6feb",
    },
    "dark_css_variables": {
        "color-brand-primary": "#58a6ff",
        "color-brand-content": "#58a6ff",
    },
    "source_repository": "https://github.com/AccursedGalaxy/noidea",
    "source_branch": "main",
    "source_directory": "docs/",
    "top_of_page_buttons": ["view"],
}
pygments_style = "friendly"
pygments_dark_style = "monokai"

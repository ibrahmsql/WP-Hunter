"""
Temodar Agent Theme Downloader

Download and extract themes for analysis.
"""

from pathlib import Path

from downloaders.plugin_downloader import PluginDownloader


class ThemeDownloader(PluginDownloader):
    """Theme downloader and extractor reusing the hardened archive flow."""

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.plugins_dir = self.base_dir / "Themes"
        self.plugins_dir.mkdir(exist_ok=True)

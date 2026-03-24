"""
WP-Hunter: WordPress Plugin & Theme Security Scanner

A reconnaissance tool for identifying vulnerable WordPress plugins and themes.
"""

from app_meta import __version__, __author__

from config import Colors, CURRENT_WP_VERSION
from models import CodeAnalysisResult, ScanConfig, PluginResult

__all__ = [
    "Colors",
    "CURRENT_WP_VERSION",
    "CodeAnalysisResult",
    "ScanConfig",
    "PluginResult",
]

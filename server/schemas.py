"""
Pydantic Models for API
"""

from typing import Optional, List, Dict, Any
from typing_extensions import Literal
from pydantic import BaseModel, Field, HttpUrl


class ScanRequest(BaseModel):
    pages: int = 5
    limit: int = 0
    min_installs: int = 1000
    max_installs: int = 0
    sort: str = "updated"
    smart: bool = False
    abandoned: bool = False
    user_facing: bool = False
    themes: bool = False
    min_days: int = 0
    max_days: int = 0
    aggressive: bool = False


class DownloadRequest(BaseModel):
    slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="WordPress slug (letters, numbers, underscore, hyphen)",
    )
    download_url: HttpUrl


class FavoritePluginRequest(BaseModel):
    slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="WordPress slug (letters, numbers, underscore, hyphen)",
    )
    name: str = Field(..., min_length=1, max_length=300)
    version: Optional[str] = Field(default=None, max_length=100)
    score: int = 0
    installations: int = 0
    days_since_update: int = 0
    tested_wp_version: Optional[str] = Field(default=None, max_length=50)
    is_theme: bool = False
    download_link: Optional[str] = Field(default=None, max_length=2000)
    wp_org_link: Optional[str] = Field(default=None, max_length=2000)
    cve_search_link: Optional[str] = Field(default=None, max_length=2000)
    wpscan_link: Optional[str] = Field(default=None, max_length=2000)
    patchstack_link: Optional[str] = Field(default=None, max_length=2000)
    wordfence_link: Optional[str] = Field(default=None, max_length=2000)
    google_dork_link: Optional[str] = Field(default=None, max_length=4000)
    trac_link: Optional[str] = Field(default=None, max_length=2000)
    author_trusted: bool = False
    is_risky_category: bool = False
    is_user_facing: bool = False
    risk_tags: List[str] = Field(default_factory=list)
    security_flags: List[str] = Field(default_factory=list)
    feature_flags: List[str] = Field(default_factory=list)
    code_analysis: Optional[Dict[str, Any]] = None


class SemgrepRuleRequest(BaseModel):
    id: str = Field(
        ...,
        min_length=1,
        max_length=120,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    pattern: str = Field(..., min_length=1, max_length=10000)
    message: str = Field(..., min_length=1, max_length=500)
    severity: Literal["ERROR", "WARNING", "INFO"] = "WARNING"
    languages: List[str] = Field(default_factory=lambda: ["php"], min_length=1)


class SemgrepRulesetRequest(BaseModel):
    ruleset: str = Field(..., min_length=1, max_length=200)


class SemgrepBulkToggleRequest(BaseModel):
    enabled: bool

"""
Pydantic models for upgrade configuration and results.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, field_validator


class GoldenImage(BaseModel):
    """Configuration for the target firmware image."""
    version: str = Field(..., description="Target firmware version")
    image_name: str = Field(..., description="Exact filename of the image")
    image_size: Optional[int] = Field(None, description="Expected size in bytes")
    md5: Optional[str] = Field(None, description="Expected MD5 checksum")
    sha256: Optional[str] = Field(None, description="Expected SHA256 checksum")

    @field_validator('image_name')
    @classmethod
    def validate_image_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("image_name cannot be empty")
        return v


class FileServer(BaseModel):
    """Configuration for the firmware file server."""
    ip: str = Field(..., description="IP address or hostname of the server")
    protocol: str = Field("http", description="Transfer protocol (http, https)")
    base_path: str = Field("", description="Base directory on the server")
    port: Optional[int] = Field(None, description="Server port")
    username: Optional[str] = None
    password: Optional[str] = None
    source_interface: Optional[str] = Field(None, description="Device interface to use for transfer")

    @field_validator('protocol')
    @classmethod
    def validate_protocol(cls, v: str) -> str:
        allowed = ['http', 'https', 'tftp', 'ftp', 'scp']
        if v.lower() not in allowed:
            raise ValueError(f"Protocol must be one of {allowed}")
        return v.lower()


class DeviceInfo(BaseModel):
    """Structure for discovered device information."""
    manufacturer: str = "Unknown"
    model: Optional[str] = None
    version: Optional[str] = None
    hostname: Optional[str] = None
    serial: Optional[str] = None
    platform: Optional[str] = None
    uptime: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class StageResult(BaseModel):
    """Result of a single upgrade stage execution."""
    success: bool
    message: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    duration: float = 0.0
    command: Optional[str] = None
    skipped: bool = False

from pydantic import BaseModel
from typing import Dict, Any, Optional


class SetConfigMessage(BaseModel):
    config_path: str
    data: Dict[str, Any]


class SysCmdMessage(BaseModel):
    type: str
    api_type: Optional[str] = None
    data: Dict[str, Any]


class SendMessage(BaseModel):
    type: str
    data: Dict[str, Any]


class LLMMessage(BaseModel):
    type: str
    username: str
    content: str


class CallbackMessage(BaseModel):
    type: str
    data: Dict[str, Any]


"""
通用
"""


class CommonResult(BaseModel):
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None

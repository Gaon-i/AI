from typing import Generic
from typing import Optional
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    status: int
    message: str
    data: Optional[T] = None
    error_code: Optional[str] = None


class HealthResponseData(BaseModel):
    status: str


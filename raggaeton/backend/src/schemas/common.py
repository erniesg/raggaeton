from pydantic import BaseModel
from typing import Optional, Union, List


class OptionalParams(BaseModel):
    data: Optional[str] = None
    publication: Optional[str] = None
    country: Optional[str] = None
    personas: Optional[Union[str, List[str]]] = None
    desired_length: Optional[int] = None
    scratchpad: Optional[str] = None
    include_token_count: Optional[bool] = False
    limit: Optional[int] = None

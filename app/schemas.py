from pydantic import BaseModel
from typing import List, Dict, Any

class CreateTransfer(BaseModel):
    course_id: int
    files: List[Dict[str, Any]]
    destination_path_prefix: str = ""

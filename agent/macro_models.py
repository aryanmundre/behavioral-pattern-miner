from pydantic import BaseModel

class Macro(BaseModel):
    apps: list[str]
    refined_steps: list[str] = []

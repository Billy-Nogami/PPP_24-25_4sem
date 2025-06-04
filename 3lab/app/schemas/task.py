from pydantic import BaseModel, Field

class TaskCreate(BaseModel):
    url: str
    client_id: str
    build_graph: bool = Field(False, description="Build site graph instead of simple parsing")

class TaskOut(BaseModel):
    id: int
    url: str
    status: str
    result: str | None

    class Config:
        orm_mode = True
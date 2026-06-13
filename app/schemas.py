from pydantic import BaseModel


class ImportResult(BaseModel):
    created: int
    updated: int
    skipped: int
    errors: list[str]

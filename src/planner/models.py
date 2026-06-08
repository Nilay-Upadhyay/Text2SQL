from pydantic import BaseModel, Field


class QueryPlan(BaseModel):
    requires_sql: bool = True

    intent: str

    tables: list[str] = Field(default_factory=list)

    metrics: list[str] = Field(default_factory=list)

    dimensions: list[str] = Field(default_factory=list)

    filters: dict = Field(default_factory=dict)

    reasoning: str
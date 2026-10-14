"""What each AI role must return, validated strictly. Anything that doesn't fit is rejected
and asked for again, never patched up silently."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from algolens.verification.compare import KINDS


class Example(BaseModel):
    args: list[Any]
    expected: Any


class Comparator(BaseModel):
    kind: Literal[KINDS] = "exact"  # type: ignore[valid-type]
    tolerance: float = Field(default=1e-6, gt=0, le=1)


class ParsedProblem(BaseModel):
    """Plan §4 ProblemSpec, as produced by the parse role."""

    in_scope: bool
    rejection_reason: str = ""
    title: str = ""
    function_name: str = ""
    params: list[dict] = []  # input schema params (algolens/schema/model.py)
    constraints: list[dict] = []
    output: str = ""  # what is returned, in words
    result_kind: Literal["binary_tree", "linked_list"] | None = None
    comparator: Comparator = Comparator()
    examples: list[Example] = []
    patterns: list[str] = []
    extra_rules_python: str = ""  # validate(*args) -> str | None, for rules the schema can't say

    @field_validator("function_name")
    @classmethod
    def _identifier(cls, v: str) -> str:
        if v and not v.isidentifier():
            raise ValueError("function_name must be a Python identifier")
        return v

    def schema_json(self) -> dict:
        return {"params": self.params, "constraints": self.constraints}

    def convert(self) -> list[str | None]:
        kinds = [p.get("type", {}).get("kind") for p in self.params]
        return [k if k in ("binary_tree", "linked_list") else None for k in kinds]


class Code(BaseModel):
    python_code: str = Field(min_length=10, max_length=60_000)
    cpp_code: str = Field(min_length=10, max_length=80_000)


class GeneratedApproach(Code):
    name: str = Field(min_length=1, max_length=80)
    key_idea: str = Field(min_length=1, max_length=300)
    time: str = Field(min_length=1, max_length=40)
    space: str = Field(min_length=1, max_length=40)


class ApproachList(BaseModel):
    approaches: list[GeneratedApproach] = Field(min_length=1, max_length=2)


class BruteB(BaseModel):
    restatement: str = ""
    python_code: str = Field(min_length=10, max_length=60_000)


class Checker(BaseModel):
    python_code: str = Field(min_length=10, max_length=30_000)

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

    @field_validator("title", "output", "rejection_reason", mode="before")
    @classmethod
    def _text(cls, v: Any) -> Any:
        """Models sometimes describe the output as a type ({"kind": "string", ...}) instead of
        a sentence. That's still a description, so keep it as text rather than reject it."""
        if v is None:
            return ""
        if isinstance(v, dict | list):
            import json

            return json.dumps(v)
        return v

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


class Understanding(BaseModel):
    restated: str = Field(min_length=1, max_length=600)
    inputs_outputs: str = Field(min_length=1, max_length=400)
    observations: list[str] = Field(min_length=1, max_length=5)
    edge_cases: list[str] = Field(default=[], max_length=5)


class DataStructure(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    why: str = Field(min_length=1, max_length=400)


class ApproachThinking(BaseModel):
    intuition: str = Field(min_length=1, max_length=600)
    bottleneck: str = Field(default="", max_length=500)  # what's slow, leading to the next idea
    data_structure: DataStructure | None = None
    steps: list[str] = Field(min_length=1, max_length=8)
    complexity_reasoning: str = Field(min_length=1, max_length=500)


class Explanation(BaseModel):
    """The interview-style thought process, from brute force to optimal (AI-written prose about
    code that has been verified)."""

    understanding: Understanding
    approaches: list[ApproachThinking] = Field(min_length=1, max_length=4)
    pattern: str = Field(min_length=1, max_length=80)
    takeaway: str = Field(min_length=1, max_length=300)

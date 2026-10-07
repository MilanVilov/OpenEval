"""Validated configuration for OpenAI Decisions questions."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StrictBool, StrictStr, model_validator

DECISION_MODEL = "gpt-6-luna"


class QuestionBase(BaseModel):
    """Common instructions and identity for a decision question."""

    model_config = {"extra": "forbid"}
    name: str = Field(min_length=1)
    instructions: str = Field(min_length=1)


class PredicateQuestion(QuestionBase):
    """Estimate the probability that a condition is true."""

    type: Literal["predicate"]


class ChoiceOption(BaseModel):
    """A discrete choice value and its meaning."""

    model_config = {"extra": "forbid"}
    value: StrictStr | StrictBool
    description: str | None = None


class ChoiceQuestion(QuestionBase):
    """Choose one distinct category."""

    type: Literal["choice"]
    choices: list[ChoiceOption] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_values(self) -> "ChoiceQuestion":
        """Reject duplicated category values."""
        values = [(type(choice.value), choice.value) for choice in self.choices]
        if len(values) != len(set(values)):
            raise ValueError("Choice values must be unique")
        return self


class ScoreLevel(BaseModel):
    """An ordered rubric level, indexed from zero."""

    model_config = {"extra": "forbid"}
    label: str = Field(min_length=1)
    description: str | None = None


class ScoreQuestion(QuestionBase):
    """Score against an ordered rubric."""

    type: Literal["score"]
    levels: list[ScoreLevel] = Field(min_length=2)


Question = Annotated[
    PredicateQuestion | ChoiceQuestion | ScoreQuestion, Field(discriminator="type")
]


class DecisionConfig(BaseModel):
    """Named questions evaluated against each dataset input."""

    model_config = {"extra": "forbid"}
    questions: list[Question] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_names(self) -> "DecisionConfig":
        """Require unique names so every answer can be identified."""
        names = [question.name for question in self.questions]
        if len(names) != len(set(names)):
            raise ValueError("Decision question names must be unique")
        return self


def validate_decision_model(model: str, decision_config: object) -> None:
    """Require Decisions questions when its dedicated model is selected."""
    if model == DECISION_MODEL and decision_config is None:
        raise ValueError("Decisions requires a decision_config with questions")
    if model != DECISION_MODEL and decision_config is not None:
        raise ValueError("Decision questions are only supported by gpt-6-luna")

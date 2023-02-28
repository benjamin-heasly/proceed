from dataclasses import dataclass, field
from typing import Any, Self
from string import Template
from pipeline_stuff.yaml_data import YamlData


def apply_args(x: Any, args: dict[str, str]):
    """Recursively apply given args to string templates found in x and its elements."""
    if isinstance(x, str):
        return Template(x).safe_substitute(args)
    elif isinstance(x, list):
        return [apply_args(e, args) for e in x]
    elif isinstance(x, dict):
        return {apply_args(k, args): apply_args(v, args) for k, v in x.items()}
    else:
        return x


@dataclass
class Step(YamlData):
    """A computation step with required inputs, expected outputs, and container run parameters."""

    name: str = ""
    image: str = ""
    volumes: dict[str, Any] = field(default_factory=dict)
    command: list[str] = field(default_factory=list)

    def with_args_applied(self, args: dict[str, str]) -> Self:
        """Construct a new Step, the result of applying given args to string fields of this Step."""
        return Step(
            name=apply_args(self.name, args),
            image=apply_args(self.image, args),
            volumes=apply_args(self.volumes, args),
            command=apply_args(self.command, args)
        )


@dataclass
class StepResult(YamlData):
    """The results of running a Step process."""

    name: str = ""
    image_id: str = ""
    exit_code: int = None
    logs: str = ""


@dataclass
class Pipeline(YamlData):
    """Top-level container for Steps to run and other pipeline configuration."""

    version: str = "0.0.1"
    args: dict[str, str] = field(default_factory=dict)
    volumes: dict[str, Any] = field(default_factory=dict)
    steps: list[Step] = field(default_factory=list)

    def with_args_applied(self, args: dict[str, str]) -> Self:
        """Construct a new Step, the result of applying given args to string fields of this Step."""
        return Pipeline(
            version=self.version,
            args=self.args,
            volumes=apply_args(self.volumes, args),
            steps=[step.with_args_applied(args) for step in self.steps]
        )


@dataclass
class PipelineResult(YamlData):
    """The results of running a whole Pipeline."""

    original: Pipeline
    applied: Pipeline
    step_results: list[StepResult]

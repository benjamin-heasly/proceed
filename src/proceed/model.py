from dataclasses import dataclass, field
from typing import Any, Self, Union
from string import Template
from proceed.yaml_data import YamlData


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
    volumes: dict[str, Union[str, dict[str, str]]] = field(default_factory=dict)
    #match_in: str = None
    #match_out: str = None
    #match_done: str = None

    #working_dir: str = None
    #gpus: str = None

    #environment: dict[str, str] = field(default_factory=dict)
    #mac_address: str = None
    #network_mode: str = None
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
    image_id: str = None
    exit_code: int = None
    logs: str = None
    #files_in: str = None
    #files_out: str = None
    #files_done: str = None
    #skipped: boolean = False


@dataclass
class Pipeline(YamlData):
    """Top-level container for Steps to run and other pipeline configuration."""

    version: str = "0.0.1"
    args: dict[str, str] = field(default_factory=dict)
    volumes: dict[str, Union[str, dict[str, str]]] = field(default_factory=dict)
    #environment: dict[str, str] = field(default_factory=dict)
    #mac_address: str = None
    #network_mode: str = None
    steps: list[Step] = field(default_factory=list)

    def combine_args(self, args: dict[str, str]) -> dict[str, str]:
        """Update self.args with given args values, but don't add new keys."""
        accepted_args = {}
        for k in self.args.keys():
            if k in args.keys():
                accepted_args[k] = args[k]
            else:
                accepted_args[k] = self.args[k]
        return accepted_args

    def with_args_applied(self, args: dict[str, str]) -> Self:
        """Construct a new Step, the result of applying given args to string fields of this Step."""
        combined_args = self.combine_args(args)
        return Pipeline(
            version=self.version,
            args=combined_args,
            volumes=apply_args(self.volumes, combined_args),
            steps=[step.with_args_applied(combined_args) for step in self.steps]
        )


@dataclass
class PipelineResult(YamlData):
    """The results of running a whole Pipeline."""

    original: Pipeline
    amended: Pipeline
    step_results: list[StepResult]
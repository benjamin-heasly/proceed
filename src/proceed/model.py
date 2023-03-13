from dataclasses import dataclass, field
from typing import Any, Self, Union
from string import Template
from proceed.yaml_data import YamlData

proceed_model_version = "0.0.1"


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

    name: str = None
    description: str = None
    image: str = None
    command: list[str] = field(default_factory=list)

    volumes: dict[str, Union[str, dict[str, str]]] = field(default_factory=dict)
    working_dir: str = None
    match_done: list[str] = field(default_factory=list)
    match_in: list[str] = field(default_factory=list)
    match_out: list[str] = field(default_factory=list)

    environment: dict[str, str] = field(default_factory=dict)
    gpus: bool = None

    network_mode: str = None
    mac_address: str = None

    def with_args_applied(self, args: dict[str, str]) -> Self:
        """Construct a new Step, the result of applying given args to string fields of this Step."""
        return Step(
            name=apply_args(self.name, args),
            description=apply_args(self.description, args),
            image=apply_args(self.image, args),
            command=apply_args(self.command, args),
            volumes=apply_args(self.volumes, args),
            working_dir=apply_args(self.working_dir, args),
            match_done=apply_args(self.match_done, args),
            match_in=apply_args(self.match_in, args),
            match_out=apply_args(self.match_out, args),
            environment=apply_args(self.environment, args),
            gpus=apply_args(self.gpus, args),
            network_mode=apply_args(self.network_mode, args),
            mac_address=apply_args(self.mac_address, args),
        )

    def with_prototype_applied(self, prototype: Self) -> Self:
        """Construct a new Step, the result of accepting default values from the given prototype."""
        if not prototype:
            return self

        return Step(
            name=self.name or prototype.name,
            description=self.description or prototype.description,
            image=self.image or prototype.image,
            command=self.command or prototype.command,
            volumes={**prototype.volumes, **self.volumes},
            working_dir=self.working_dir or prototype.working_dir,
            match_done=self.match_done or prototype.match_done,
            match_in=self.match_in or prototype.match_in,
            match_out=self.match_out or prototype.match_out,
            environment={**prototype.environment, **self.environment},
            gpus=self.gpus or prototype.gpus,
            network_mode=self.network_mode or prototype.network_mode,
            mac_address=self.mac_address or prototype.mac_address
        )


@dataclass
class Timing(YamlData):
    """Keep track of a start time, an end time, and the duration."""

    start: str = None
    finish: str = None
    duration: float = None

    def is_complete(self):
        return self.start is not None and self.finish is not None and self.duration > 0


@dataclass
class StepResult(YamlData):
    """The results of running a Step process."""

    name: str = None
    image_id: str = None
    exit_code: int = None
    log_file: str = None
    timing: Timing = field(compare=False, default=None)
    files_done: dict[str, dict[str, str]] = field(default_factory=dict)
    files_in: dict[str, dict[str, str]] = field(default_factory=dict)
    files_out: dict[str, dict[str, str]] = field(default_factory=dict)
    skipped: bool = False


@dataclass
class Pipeline(YamlData):
    """Top-level container for Steps to run and other pipeline configuration."""

    version: str = proceed_model_version
    description: str = None
    args: dict[str, str] = field(default_factory=dict)
    prototype: Step = None
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
        if self.prototype:
            amended_prototype = self.prototype.with_args_applied(combined_args)
        else:
            amended_prototype = None
        return Pipeline(
            version=self.version,
            description=self.description,
            args=combined_args,
            prototype=amended_prototype,
            steps=[step.with_args_applied(combined_args) for step in self.steps]
        )

    def with_prototype_applied(self) -> Self:
        return Pipeline(
            version=self.version,
            description=self.description,
            args=self.args,
            prototype=self.prototype,
            steps=[step.with_prototype_applied(self.prototype) for step in self.steps]
        )


@dataclass
class PipelineResult(YamlData):
    """The results of running a whole Pipeline."""

    original: Pipeline = None
    amended: Pipeline = None
    timing: Timing = field(compare=False, default=None)
    step_results: list[StepResult] = field(default_factory=list)

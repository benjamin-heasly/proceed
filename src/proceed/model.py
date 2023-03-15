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
    """What's in a name?"""

    description: str = None
    """I'm a description."""

    image: str = None
    """What's in a name?"""
    command: list[str] = field(default_factory=list)
    """What's in a name?"""

    volumes: dict[str, Union[str, dict[str, str]]] = field(default_factory=dict)
    """Host directories to make available inside the step's container.

    This is a key-value mapping from host absolute paths to container absolute paths.
    The keys are strings (host absolute paths).
    The values are either strings (container absolute paths) or detailed key-value mappings.

    .. code-block:: yaml

        steps:
          - name: volumes example
            volumes:
              /host/simple: /simple
              /host/read-only: {bind: /read-only, mode: ro}
              /host/read-write: {bind: /read-write, mode: rw}

    The detailed style lets you specify the container path to bind as well as the read/write permissions.

    bind
        the container absolute path to bind (where the host dir will show up inside the container)

    mode
        the read/write permission to give the container: "rw" for read plus write (the default), "ro" for read only
    """

    working_dir: str = None
    """What's in a name?"""
    match_done: list[str] = field(default_factory=list)
    """What's in a name?"""
    match_in: list[str] = field(default_factory=list)
    """What's in a name?"""
    match_out: list[str] = field(default_factory=list)
    """What's in a name?"""

    environment: dict[str, str] = field(default_factory=dict)
    """What's in a name?"""
    gpus: bool = None
    """What's in a name?"""

    network_mode: str = None
    """What's in a name?"""
    mac_address: str = None
    """What's in a name?"""

    def _with_args_applied(self, args: dict[str, str]) -> Self:
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

    def _with_prototype_applied(self, prototype: Self) -> Self:
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

    def _is_complete(self):
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

    def _combine_args(self, args: dict[str, str]) -> dict[str, str]:
        """Update self.args with given args values, but don't add new keys."""
        accepted_args = {}
        for k in self.args.keys():
            if k in args.keys():
                accepted_args[k] = args[k]
            else:
                accepted_args[k] = self.args[k]
        return accepted_args

    def _with_args_applied(self, args: dict[str, str]) -> Self:
        """Construct a new Step, the result of applying given args to string fields of this Step."""
        combined_args = self._combine_args(args)
        if self.prototype:
            amended_prototype = self.prototype._with_args_applied(combined_args)
        else:
            amended_prototype = None
        return Pipeline(
            version=self.version,
            description=self.description,
            args=combined_args,
            prototype=amended_prototype,
            steps=[step._with_args_applied(combined_args) for step in self.steps]
        )

    def _with_prototype_applied(self) -> Self:
        return Pipeline(
            version=self.version,
            description=self.description,
            args=self.args,
            prototype=self.prototype,
            steps=[step._with_prototype_applied(self.prototype) for step in self.steps]
        )


@dataclass
class PipelineResult(YamlData):
    """The results of running a whole Pipeline."""

    original: Pipeline = None
    amended: Pipeline = None
    timing: Timing = field(compare=False, default=None)
    step_results: list[StepResult] = field(default_factory=list)

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
    """Specification for a container-based processing step.

    Most :class:`Step` attributes are optional, but :attr:`name` is required
    in order to distinguish steps from each other, and :attr:`image` is required
    in order to actually run anything.
    """

    name: str = None
    """Any name for the step, unique within a :class:`Pipeline` (required)."""

    description: str = None
    """Any description to save along with the step.

    The step description is not used during pipeline execution.
    It's provided as a convenience to support user documentation,
    notes-to-self, audits, etc.

    Unlike code comments or YAML comments, the description is saved
    as part of the execution record.
    """

    image: str = None
    """The tag or id of the container image to run from (required).

    The image is the most important part of each step!
    It provides the step's executables, dependencies, and basic environment.


    The image may be a human-readable tag of the form ``group/name:version``
    (like on `Docker Hub <https://hub.docker.com/>`_) or a unique ``IMAGE ID``
    (like the output of ``docker images``).

    .. code-block:: yaml

        steps:
          - name: human readable example
            image: mathworks/matlab:r2022b
          - name: image id example
            image: d209dd14c3c4
    """

    command: list[str] = field(default_factory=list)
    """The command to run inside the container.

    The step command is passed to the entrypoint executable of the :attr:`image`.
    To use the default ``cmd`` of the :attr:`image`, omit this :attr:`command`.

    The command should be given as a list of string arguments.
    The list form makes it clear which argument is which and avoids confusion
    around spaces and quotes.

    .. code-block:: yaml

        steps:
          - name: command example
            image: ubuntu
            command: ["echo", "hello world"]
    """

    volumes: dict[str, Union[str, dict[str, str]]] = field(default_factory=dict)
    """Host directories to make available inside the step's container.

    This is a key-value mapping from host absolute paths to container absolute paths.
    The keys are strings (host absolute paths).
    The values are strings (container absolute paths) or detailed key-value mappings.

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
        the read/write permission to give the container: ``rw`` for read plus write (the default), ``ro`` for read only
    """

    working_dir: str = None
    """A working directory path within the container -- the initial shell ``pwd`` or Python ``os.getcwd()``."""

    match_done: list[str] = field(default_factory=list)
    """File matching patterns to search for, before deciding to run the step.

    This is a list of `glob <https://docs.python.org/3/library/glob.html>`_
    patterns to search for before running the step.
    Each of the step's :attr:`volumes` will be searched with the same list of patterns.

    If any matches are found, these files will be noted in the execution record,
    along with their content digests, and the step will be skipped.
    This is intended as a convenience to avoid redundant processing.
    To make a step run unconditionally, omit :attr:`match_done`.

    .. code-block:: yaml

        steps:
          - name: match done example
            match_done:
              - one/specific/file.txt
              - any/text/*.txt
              - any/text/any/subdir/**/*.txt
    """

    match_in: list[str] = field(default_factory=list)
    """File matching patterns to search for, before running the step.

    This is a list of `glob <https://docs.python.org/3/library/glob.html>`_
    patterns to search for before running the step.
    Each of the step's :attr:`volumes` will be searched with the same list of patterns.

    Any matches found will be noted in the execution record.
    :attr:`match_in` is intended to support audits by accounting for the input files
    that went into a step, along with their content digests.
    Unlike :attr:`match_done`, :attr:`match_in` does not affect step execution.

    .. code-block:: yaml

        steps:
          - name: match in example
            match_in:
              - one/specific/file.txt
              - any/text/*.txt
              - any/text/any/subdir/**/*.txt
    """

    match_out: list[str] = field(default_factory=list)
    """File matching patterns to search for, after running the step.

    This is a list of `glob <https://docs.python.org/3/library/glob.html>`_
    patterns to search for after running the step.
    Each of the step's :attr:`volumes` will be searched with the same list of patterns.

    Any matches found will be noted in the execution record.
    :attr:`match_out` is intended to support audits by accounting for the output files
    that came from a step, along with their content digests.
    Unlike :attr:`match_done`, :attr:`match_out` does not affect step execution.

    .. code-block:: yaml

        steps:
          - name: match out example
            match_out:
              - one/specific/file.txt
              - any/text/*.txt
              - any/text/any/subdir/**/*.txt
    """

    environment: dict[str, str] = field(default_factory=dict)
    """Environment variables to set inside the step's container.

    This is a key-value mapping from environment variable names to values.
    The keys and values are both strings.

    .. code-block:: yaml

        steps:
          - name: environment example
            environment:
              MLM_LICENSE_FILE: /license.lic
              foo: bar
    """

    gpus: bool = None
    """Whether or not to request GPU device support.

    When :attr:`gpus` is ``true``, request GPU device support similar to the
    Docker run ``--gpus all``
    `resource request <https://docs.docker.com/config/containers/resource_constraints/#gpu>`_.
    """

    network_mode: str = None
    """How to configure the container's network environment.

    When provided, this should be one of the following
    `network modes <https://docker-py.readthedocs.io/en/stable/containers.html>`_:

    bridge
      create an isolated network environment for the container (default)

    none
      disable networking for the container

    container:<name|id>
      reuse the network of another container, by name or id

    host
      make the container's network environment just like the host's
    """

    mac_address: str = None
    """Aribtrary MAC address to set in the container.

    Perhaps surprisingly, containers can have arbitrary `MAC <https://en.wikipedia.org/wiki/MAC_address>`_
    "hardware" addresses.

    .. code-block:: yaml

        steps:
          - name: mac address example
            mac_address: aa:bb:cc:dd:ee:ff
    """

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

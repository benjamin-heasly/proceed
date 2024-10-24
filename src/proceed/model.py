from dataclasses import dataclass, field
from typing import Any, Self, Union
from string import Template

from proceed.yaml_data import YamlData
from proceed.__about__ import __version__ as proceed_version


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
    """Specifies a container-based processing step.

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
    as part of the :class:`ExecutionRecord`.
    """

    image: str = None
    """The tag or id of the container image to run from (required).

    The :attr:`image` is the most important part of each step!
    It provides the step's executables, dependencies, and basic environment.

    The image may be a human-readable tag of the form ``group/name:version``
    (like on `Docker Hub <https://hub.docker.com/>`_) or a unique id
    (like the ``IMAGE ID`` output of ``docker images``).

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

    If any matches are found, these files will be noted in the :class:`ExecutionRecord`,
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

    Any matches found will be noted in the :class:`ExecutionRecord`.
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

    Any matches found will be noted in the :class:`ExecutionRecord`.
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

    match_summary: list[str] = field(default_factory=list)
    """File matching patterns to search for, after running the step, to include when summarizing results.

    This is a list of `glob <https://docs.python.org/3/library/glob.html>`_
    patterns to search for after running the step.
    Each of the step's :attr:`volumes` will be searched with the same list of patterns.

    Any matches found will be noted in the :class:`ExecutionRecord`.
    :attr:`match_summary` is intended to enrich pipeline execution summaries with custom columns.
    See :attr:`StepResult.files_summary` for how matched files are treated.
    Unlike :attr:`match_done`, :attr:`match_summary` does not affect step execution.

    .. code-block:: yaml

        steps:
          - name: match summary example
            match_summary:
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

    gpus: str | bool = None
    """Whether or not to request GPU device support.

    When :attr:`gpus` is ``True`` / truthy, request GPU device support similar to the
    Docker run ``--gpus all``.  Note: the empty string ``""`` will be treated as ``False``.
    `resource request <https://docs.docker.com/config/containers/resource_constraints/#gpu>`_.

    .. code-block:: yaml

        steps:
          - name: gpus example
            gpus: true
    """

    user: str | int = None
    """User (and group) to run as in the container, instead of container default (usually root).

    When :attr:`user` is omitted or ``None`` the container will run with the default user
    and group specified in the image.  This is usually root, or sometimes an image-specific
    user and group.

    When :attr:`user` is provided it must be a string user name or int uid, with group/gid optional,
    as follows:

    self or self:group
      The special user name ``self`` means run with the uid of the current user on the Docker host.
      Optionally, this can be followed by a group name or gid as in ``self:group``.
      When this ``group`` is a string name it must exists on the Docker host and will be converted to a host gid.

    user or user:group
      Other string user names and group names are used as-is and must exist within the image / container.

    uid or uid:gid
      Integer uids and gids don't have to exist within the image / container.
      It's proably helpful if they exist on the Docker host.

    .. code-block:: yaml

        steps:
          - name: default/root user example
        steps:
          - name: host current user and group example
            user: self
        steps:
          - name: existing container user example
            user: container-user
        steps:
          - name: integer uid and gid example
            user: 1234:5678
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

    shm_size: str = None
    """Max size of the ``/dev/shm`` shared memory in-memory-file-system.

    Docker defaults ``/dev/shm`` to 64 megabytes.
    Steps that need more can use :attr:`shm_size` to increase this limit.
    Integer values will be treated as bytes, for example ``1000``.
    Values with a unit suffix will use larger units, for example `10b`, `10k`, `10m`, or `10g`.

    .. code-block:: yaml

        steps:
          - name: more-shm
            shm_size: 2g
    """

    privileged: bool = False
    """Whether the step's container should run with elevated privileges and device access.

    This defaults to ``False``.
    Please only set :attr:`privileged` to ``True`` temporarily, for troubleshooting!

    .. code-block:: yaml

        steps:
          - name: elevated-privileged
            privileged: True
    """

    X11: bool = False
    """Whether to set up the container as an X11 client app with ``DISPLAY`` access.

    This defaults to ``False``, assuming most steps are noninteractive.
    Set :attr:`X11` to ``True`` to set up the container as an X11 GUI client app with ``DISPLAY`` access.
    This will modify the container environment in a few ways:

    ``DISPLAY``
      Proceed will set the ``DISPLAY`` environment variable in the step container to match the host environment.

    ``/tmp/.X11-unix``
      If the ``/tmp/.X11-unix`` directory exists on the host Proceed will add this to the step's :attr:`Step.volumes`.
      This lets the step container access local Unix sockets for connecting to a local X server.

    :attr:`Step.network_mode` ``host``
      Proceed will set the step's network mode to ``host``.
      This lets the step container access TCP sockets for connecting to a remote/proxied X server as with `ssh -X` or `ssh -Y`.

    ``XAUTHORITY``
      Proceed will set up the ``XAUTHORITY`` environment variable and ``.Xauthority`` cookie file based on the host environment.
      If the ``XAUTHORITY`` variable is set in the host environment Proceed will use this file path to locate the cookie file.
      Otherwise Proceed will use the default cookie file path which is the current host user's ``$HOME/.Xauthority``.
      If the cookie file exists on the host Proceed will add it to the step's :attr:`Step.volumes`.
      Proceed will bind the cookie file to a fixed, known path in the container like ``/var/.Xauthority``.
      Proceed will set the ``XAUTHORITY`` environment variable in the container to the same known path.
      Using a fixed path for the cookie file should avoid any dependency on the container user or HOME configuration (or lack thereof).
      All of this lets the step container authenticate with a remote/proxied X server as with `ssh -X` or `ssh -Y`.

    .. code-block:: yaml

        steps:
          - name: x11-gui-client
            X11: True
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
            match_summary=apply_args(self.match_summary, args),
            environment=apply_args(self.environment, args),
            gpus=apply_args(self.gpus, args),
            network_mode=apply_args(self.network_mode, args),
            mac_address=apply_args(self.mac_address, args),
            user=apply_args(self.user, args),
            shm_size=apply_args(self.shm_size, args),
            privileged=apply_args(self.privileged, args),
            X11=apply_args(self.X11, args)
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
            match_summary=self.match_summary or prototype.match_summary,
            environment={**prototype.environment, **self.environment},
            gpus=self.gpus or prototype.gpus,
            network_mode=self.network_mode or prototype.network_mode,
            mac_address=self.mac_address or prototype.mac_address,
            user=self.user or prototype.user,
            shm_size=self.shm_size or prototype.shm_size,
            privileged=self.privileged or prototype.privileged,
            X11=self.X11 or prototype.X11
        )


@dataclass
class Timing(YamlData):
    """Records :class:`Step` and :class:`Pipeline` execution times and durations."""

    start: str = None
    """Datetime UTC when a :class:`Step` or :class:`Pipeline` started running.

    The datetime uses `ISO <https://en.wikipedia.org/wiki/ISO_8601>`_ format ``YYYY-MM-DDTHH:MM:SS.mmmmmm``.
    """

    finish: str = None
    """Datetime UTC when a :class:`Step` or :class:`Pipeline` finished running.

    The datetime uses `ISO <https://en.wikipedia.org/wiki/ISO_8601>`_ format ``YYYY-MM-DDTHH:MM:SS.mmmmmm``.
    """

    duration: float = None
    """Duration in seconds from :attr:`start` to :attr:`finish`."""

    def _is_complete(self):
        return self.start is not None and self.finish is not None and self.duration > 0


@dataclass
class StepResult(YamlData):
    """Records what happened when a :class:`Step` ran."""

    name: str = None
    """The name of the :class:`Step` that ran."""

    image_id: str = None
    """The unique id of the :attr:`Step.image` that was used.

    This :attr:`image_id` is always a unique id
    (like the ``IMAGE ID`` output of ``docker images``),
    even if the step's :attr:`Step.image` was given as a human-readable tag.
    This avoids ambiguitiy from mutable tags like ``:latest``.
    """

    exit_code: int = None
    """The exit code / status code of the step's container process.

    Exit code ``0`` is interpreted as success, nonzero as failure.
    """

    log_file: str = None
    """The host path to the log file with step console output (stdout and stderr)."""

    timing: Timing = field(compare=False, default=None)
    """Start datetime, finish datetime, and duration for the step's container process."""

    files_done: dict[str, dict[str, str]] = field(default_factory=dict)
    """Files that matched the :attr:`Step.match_done` pattern.

    This is a key-value mapping from host :attr:`Step.volumes` paths to matched files.
    The keys are strings (host volume paths).
    The values are nested key-value mappings,
    where the keys are matched file paths within a volume
    and the values are content hash digests of the matched files.

    .. code-block:: yaml

        step_results:
          - name: files done example
            files_done:
              /host/volume: {done_file.txt: 'sha256:5f386141...'}
            skipped: true

    When :attr:`files_done` is nonempty the :class:`Step` is considered
    to be already complete before running, and :attr:`skipped` should be ``True``.
    """

    files_in: dict[str, dict[str, str]] = field(default_factory=dict)
    """Files that matched the :attr:`Step.match_in` pattern.

    This is a key-value mapping from host :attr:`Step.volumes` paths to matched files.
    The keys are strings (host volume paths).
    The values are nested key-value mappings,
    where the keys are matched file paths within a volume
    and the values are content hash digests of the matched files.

    .. code-block:: yaml

        step_results:
          - name: files in example
            files_in:
              /host/volume/a: {first_match.txt: 'sha256:93d4e5c7...', second_match.txt: 'sha256:d1b54ec5...'}
              /host/volume/b: {third_match.txt: 'sha256:a4619a89...'}

    Unlike :attr:`files_done`, :attr:`files_in` does not affect step execution.
    :attr:`files_in` is intended to support auditing for reproducibility
    and comparisons to files used in other steps or pipeline executions.
    """

    files_out: dict[str, dict[str, str]] = field(default_factory=dict)
    """Files that matched the :attr:`Step.match_out` pattern.

    This is a key-value mapping from host :attr:`Step.volumes` paths to matched files.
    The keys are strings (host volume paths).
    The values are nested key-value mappings,
    where the keys are matched file paths within a volume
    and the values are content hash digests of the matched files.

    .. code-block:: yaml

        step_results:
          - name: files out example
            files_out:
              /host/volume/a: {first_match.txt: 'sha256:93d4e5c7...', second_match.txt: 'sha256:d1b54ec5...'}
              /host/volume/b: {third_match.txt: 'sha256:a4619a89...'}

    Unlike :attr:`files_done`, :attr:`files_out` does not affect step execution.
    :attr:`files_out` is intended to support auditing for reproducibility
    and comparisons to files used in other steps or pipeline executions.
    """

    files_summary: dict[str, dict[str, str]] = field(default_factory=dict)
    """Files that matched the :attr:`Step.match_summary` pattern, to include when summarizing results.

    This is a key-value mapping from host :attr:`Step.volumes` paths to matched files.
    The keys are strings (host volume paths).
    The values are nested key-value mappings,
    where the keys are matched file paths within a volume
    and the values are content hash digests of the matched files.

    .. code-block:: yaml

        step_results:
          - name: files summary example
            files_summary:
              /host/volume/a: {first_match.txt: 'sha256:93d4e5c7...', second_match.txt: 'sha256:d1b54ec5...'}
              /host/volume/b: {third_match.txt: 'sha256:a4619a89...'}

    Unlike :attr:`files_done`, :attr:`files_summary` does not affect step execution.
    :attr:`files_summary` is intended to enrich pipeline execution summaries with custom columns.

    When creating a pipeline execution summary (as with ``proceed summarize ...``)
    each file from :attr:`files_summary` will be parsed for one or more key-value pairs.
    Any keys found will be added as columns to the summery document.
    Values found will be added in corresponding columns and rows for the the same step.
    The parsing works as follows:

    YAML
    Matching YAML files will be parsed for top-level key-value mappings.
    Keys and values will be taken from within the YAML document.

    Other
    Other matching files will be teated as plaintext.
    The file name will be taken as one key, and the file text content be taken as the corresponding value.
    """

    skipped: bool = False
    """Whether a step was skipped (``True``) or actually executed (``False``).

    .. code-block:: yaml

        step_results:
          - name: step skipped example
            skipped: true
            files_done:
              /host/volume: {done_file.txt: 'sha256:5f386141...'}

    When :attr:`files_done` is nonempty the :class:`Step` is considered
    to be already complete before running, and :attr:`skipped` should be ``True``.
    """


@dataclass
class Pipeline(YamlData):
    """Specifies top-level pipeline configuration and processing steps.

    Most :class:`Pipeline` attributes are optional, but :attr:`steps` is required
    in order to actually run anything.
    """

    version: str = proceed_version
    """Which version of the Proceed :class:`Pipeline` specification, itself.

    You don't need to set the :attr:`version`.
    It might be used by Proceed iteslf to check for version compatibility.
    """

    description: str = None
    """Any description to save along with the pipeline.

    The pipeline description is not used during execution.
    It's provided as a convenience to support user documentation,
    notes-to-self, audits, etc.

    Unlike code comments or YAML comments, the description is saved
    as part of the :class:`ExecutionRecord`.
    """

    args: dict[str, str] = field(default_factory=dict)
    """Expected arguments that apply to the pipeline specification at runtime.

    This is a key-value mapping from arg names to default values.
    The keys and values are both strings.

    Pipeline :attr:`args` allow for controlled, explicit configuration of the
    pipeline at runtime.  This is intended to make pipelines somewhat dynamic
    and portable without losing track of the dynamic values that were actually
    used.

    Before pipeline execution, given and default args values will be merged
    then applied to the pipeline's :attr:`prototype` and :attr:`steps`.
    This means occurrences of arg names prefixed with ``$`` or surrounded with
    ``${ ... }`` will be replaced with the corresponding arg value
    (see YAML examples below).

    After execution, the arg values that were used as well as the amended
    :attr:`prototype` and :attr:`steps` will be saved in the :class:`ExecutionRecord`.
    This should reduce guesswork about what was actually executed.

    Here are two examples of how you might use :attr:`args`:

    Host-specific ``data_dir``
      Your laptop might have a folder with data files in it, and your
      collaborators might have similar folders on their laptops.  You could
      write a pipeline  that expects a ``data_dir`` arg, allowing the
      host-specific ``data_dir`` to be supplied at runtime.  This way everyone
      could use the exact same pipeline specification.

    Daily ``data_file``
      You might have a pipeline that runs once a day, to process that day's
      data.  You could write a pipeline that expects a ``data_file`` arg,
      allowing the name of each day's data file to be supplied at runtime.
      The same exact pipeline specification could be reused each day.

    Here's an example YAML pipeline spec that declares two expected
    :attr:`args` and a step that makes use of the args as
    ``$data_dir`` (prefix style) and ``${data_file}`` (surrounding style).

    .. code-block:: yaml

        args:
          data_dir: /default/data_dir
          data_file: default_file
        steps:
          - name: args example
            image: ubuntu
            command: ["echo", "Working on: $data_dir/${data_file}.txt"]

    Here's an example YAML :class:`ExecutionRecord` for that same pipeline.
    In this example, let's assume that a custom ``data_dir`` was supplied
    at runtime as ``data_dir=/custom/data_dir``.  Let's assume the
    ``data_file`` was left with its default value.

    .. code-block:: yaml

        original:
          args:
            data_dir: /default/data_dir
            data_file: default_file
          steps:
            - name: args example
              image: ubuntu
              command: ["echo", "Working on: $data_dir/${data_file}.txt"]
        amended:
          args:
            data_dir: /custom/data_dir
            data_file: default_file
          steps:
            - name: args example
              image: ubuntu
              command: ["echo", "Working on: /custom/data_dir/default_file.txt"]

    The ``original`` is just the same as the original pipeline spec.

    The ``amended`` :attr:`args` are all the exact values used at execution time,
    whether custom or default.  The ``amended`` :attr:`steps` have had
    ``$`` and ``${ ... }`` placeholders replaced by concrete values.
    It's the ``amended`` steps that are actually executed.
    """

    prototype: Step = None
    """A :class:`Step` or partial :class:`Step` with attributes that apply to all :attr:`steps` in the pipeline.

    The :attr:`prototype` can have the same attributes as any :class:`Step`.
    You can use prototype attributes to "factor out" attribute values that
    pipeline :attr:`steps` have in common.

    Before pipeline execution, attributes provided for the :attr:`prototype`
    will be applied to each step and used if the step doesn't already have
    its own value for the same attribute.

    After execution, the amended steps will be saved in the :class:`ExecutionRecord`.
    This should reduce guesswork about what was actually executed.

    Here's an example YAML pipeline spec with a :attr:`prototype` that specifies
    the :attr:`Step.image` once, to be used by all steps.

    .. code-block:: yaml

        prototype:
          image: ubuntu
        steps:
          - name: prototype example one
            command: ["echo", "one"]
          - name: prototype example two
            command: ["echo", "two"]

    Here's an example YAML :class:`ExecutionRecord` for that same pipeline.

    .. code-block:: yaml

        original:
          prototype:
            image: ubuntu
          steps:
            - name: prototype example one
              command: ["echo", "one"]
            - name: prototype example two
              command: ["echo", "two"]
        amended:
          prototype:
            image: ubuntu
          steps:
            - name: prototype example one
              image: ubuntu
              command: ["echo", "one"]
            - name: prototype example two
              image: ubuntu
              command: ["echo", "two"]

    The ``original`` is just the same as the original pipeline spec.

    The ``amended`` :attr:`steps` have their :attr:`Step.image` filled in
    from the :attr:`prototype`.
    It's the ``amended`` steps that are actually executed.
    """

    steps: list[Step] = field(default_factory=list)
    """The list of :class:`Step` to execute.

    The :attr:`steps` are the most important part of a pipeline!
    These determine what will actually be executed.

    Before pipeline execution, all :attr:`steps` will be amended with
    :attr:`args` and the :attr:`prototype`.

    Execution will proceed by runnung each step in the order given.
    A step might be skipped, based on :attr:`Step.match_done`.
    If a step stops with a nonzero :attr:`StepResult.exit_code`, the
    pipeline execution will stop at that point.

    After execution, the :class:`ExecutionRecord` will contain a list of
    :class:`StepResult`, one for each of the :attr:`steps` executed.
    """

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
class ExecutionRecord(YamlData):
    """Auditable record of what happened when a :class:`Pipeline` was amended and executed."""

    original: Pipeline = None
    """The original :class:`Pipeline` specification, as given."""

    amended: Pipeline = None
    """The :class:`Pipeline` amended with :attr:`Pipeline.args` and :attr:`Pipeline.prototype`.

    It's the amended pipeline that's actually executed.
    """

    timing: Timing = field(compare=False, default=None)
    """Start datetime, finish datetime, and duration for the entire pipeline execution."""

    step_results: list[StepResult] = field(default_factory=list)
    """List of :class:`StepResult` from runnung the :attr:`Pipeline.steps`

    The :attr:`step_results` should correspond one-to-one with the :attr:`Pipeline.steps`.
    """

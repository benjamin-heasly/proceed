import logging
import yaml
from typing import Any
from pathlib import Path
from argparse import Action
from dataclasses import dataclass, field, fields


def parse_key_value_pairs(values: list[str], delimiter: str = "=", convert_values: bool = False):
    key_value_pairs = {}
    for kvp in values:
        (k, v) = kvp.split(delimiter)
        if convert_values:
            v = yaml.safe_load(v)
        key_value_pairs[k] = v
    return key_value_pairs


class KeyValuePairsAction(Action):
    def __call__(self, parser, namespace, values, option_string=None):
        key_value_pairs = parse_key_value_pairs(values, convert_values=False)
        setattr(namespace, self.dest, key_value_pairs)


class ConvertingKeyValuePairsAction(Action):
    def __call__(self, parser, namespace, values, option_string=None):
        key_value_pairs = parse_key_value_pairs(values, convert_values=True)
        setattr(namespace, self.dest, key_value_pairs)


@dataclass
class ConfigOption():
    value: Any = None
    cli_long_name: str = None
    cli_short_name: str = None
    cli_nargs: str = None
    cli_type: type = str
    cli_action: Any = None
    cli_help: str = None
    cli_help_default: str = "%(default)s"

    def cli_help_with_default(self):
        return f"{self.cli_help} (default: {self.cli_help_default})"

    def cli_kwargs(self) -> dict[str, Any]:
        kwargs = {
            "default": self.value,
            "action": self.cli_action,
            "help": self.cli_help_with_default(),
        }

        # Annoying: actions like "store_true" blow up when unused args provided.
        if self.cli_type:
            kwargs["type"] = self.cli_type

        if self.cli_nargs:
            kwargs["nargs"] = self.cli_nargs

        return kwargs


@dataclass
class ConfigOptions():
    """TODO: describe options for sphinx docs"""

    user_options_file: ConfigOption = field(default_factory=lambda: ConfigOption(
        value="~/proceed_options.yaml",
        cli_long_name="--user-options-file",
        cli_short_name="-u",
        cli_help="a user-level options file to search for",
    ))

    local_options_file: ConfigOption = field(default_factory=lambda: ConfigOption(
        value="./proceed_options.yaml",
        cli_long_name="--local-options-file",
        cli_short_name="-l",
        cli_help="a local options file to search for",
    ))

    custom_options_file: ConfigOption = field(default_factory=lambda: ConfigOption(
        cli_long_name="--custom-options-file",
        cli_short_name="-o",
        cli_help="an artibrary, custom options file to apply, for example: -o my_options.yaml",
    ))

    results_dir: ConfigOption = field(default_factory=lambda: ConfigOption(
        value="./proceed_out",
        cli_long_name="--results-dir",
        cli_short_name="-d",
        cli_help="working dir to receive logs and execution records",
    ))

    results_group: ConfigOption = field(default_factory=lambda: ConfigOption(
        cli_long_name="--results-group",
        cli_short_name="-g",
        cli_help="working subdir grouping outputs from the same spec",
        cli_help_default="base name of the given spec",
    ))

    results_id: ConfigOption = field(default_factory=lambda: ConfigOption(
        cli_long_name="--results-id",
        cli_short_name="-i",
        cli_help="working subdir with outputs from the current run",
        cli_help_default="UTC datetime",
    ))

    args: ConfigOption = field(default_factory=lambda: ConfigOption(
        value={},
        cli_long_name="--args",
        cli_short_name="-a",
        cli_nargs="+",
        cli_action=KeyValuePairsAction,
        cli_help="one or more arg=value assignments to apply to the pipeline, for example: --args foo=bar baz=quux",
        cli_help_default="no args",
    ))

    force_rerun: ConfigOption = field(default_factory=lambda: ConfigOption(
        value=False,
        cli_long_name="--force-rerun",
        cli_short_name="-F",
        cli_action="store_true",
        cli_type=None,
        cli_help="force steps to rerun, even if they have done files",
    ))

    step_names: ConfigOption = field(default_factory=lambda: ConfigOption(
        cli_long_name="--step-names",
        cli_short_name="-n",
        cli_nargs="+",
        cli_type=str,
        cli_help="explicit list of step names to run",
        cli_help_default="run all steps",
    ))

    summary_file: ConfigOption = field(default_factory=lambda: ConfigOption(
        value="./summary.csv",
        cli_long_name="--summary-file",
        cli_short_name="-f",
        cli_help="output file to to receive summary of results from multiple runs",
    ))

    summary_sort_rows_by: ConfigOption = field(default_factory=lambda: ConfigOption(
        value=["step_start", "file_path"],
        cli_long_name="--summary-sort-rows-by",
        cli_short_name="-s",
        cli_nargs="+",
        cli_help="summary column names by which to sort summary rows",
        cli_help_default="-s step_start file_path",
    ))

    summary_columns: ConfigOption = field(default_factory=lambda: ConfigOption(
        cli_long_name="--summary-columns",
        cli_short_name="-c",
        cli_nargs="+",
        cli_help="column names to keep in the summary",
        cli_help_default="all columns",
    ))

    yaml_skip_empty: ConfigOption = field(default_factory=lambda: ConfigOption(
        value=True,
        cli_long_name="--yaml-skip-empty",
        cli_short_name="-e",
        cli_type=bool,
        cli_help="whether to omit null and empty values from YAML outputs",
    ))

    yaml_options: ConfigOption = field(default_factory=lambda: ConfigOption(
        value={"sort_keys": False, "default_flow_style": None, "width": 1000},
        cli_long_name="--yaml-options",
        cli_short_name="-y",
        cli_nargs="+",
        cli_action=ConvertingKeyValuePairsAction,
        cli_help="one or more key=value assignments to pass as keyword args to PyYAML safe_dump()",
        cli_help_default="-y sort_keys=False default_flow_style=null width=1000",
    ))

    def option_names(self) -> list[str]:
        """Retrun a list of field names so we can iterate over the options."""
        return [field.name for field in fields(self) if field.type == ConfigOption]

    def config_option(self, option_name: str) -> ConfigOption:
        """Get the :class:`ConfigOption` with the given name -- which includes value and cli metadata."""
        return getattr(self, option_name)

    def get_value(self, option_name: str) -> Any:
        """Get the value of the option with the given name."""
        return self.config_option(option_name).value

    def set_value(self, option_name: str, value: Any):
        """Set the given value to the option with the given name."""
        self.config_option(option_name).value = value

    def update_values(self, values: dict[str, str]):
        """Set any non-default option values from the given dictionary."""
        if not values:
            return

        default_config_options = ConfigOptions()
        for option_name in self.option_names():
            if option_name in values.keys():
                value = values[option_name]
                self_value = self.get_value(option_name)
                default_value = default_config_options.get_value(option_name)
                if isinstance(self_value, dict) and isinstance(value, dict):
                    self.get_value(option_name).update(value)
                elif value != default_value:
                    self.set_value(option_name, value)

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary with the names and values of all options, omitting cli metadata."""
        return {option_name: self.get_value(option_name) for option_name in self.option_names()}


def resolve_config_options(preferred_options: dict[str, Any] = {}) -> ConfigOptions:
    """Resolve the combined, effective config options from among several possible sources.

    Search for Proceed :class:`ConfigOptions` from several possible sources.
    Return a single, effective config options combining all the sources found, in the following order:

    #. general defaults from the :class:`ConfigOptions` source code (least preferred)
    #. user-level options file, by default: ``~/proceed_options.yaml``
    #. local options file, by default: ``./proceed_options.yaml``
    #. custom options file, as passed on the command line, for example ``proceed --options=my_options.yaml ...``
    #. explicit options values, as passed on the command line (see ``proceed --help``) (most preferred)
    """

    config_options = ConfigOptions()

    user_options_file = preferred_options.get("user_options_file", config_options.user_options_file.value)
    config_options.update_values(safe_load_config_options(user_options_file))

    local_options_file = preferred_options.get("local_options_file", config_options.local_options_file.value)
    config_options.update_values(safe_load_config_options(local_options_file))

    custom_options_file = preferred_options.get("custom_options_file", config_options.custom_options_file.value)
    config_options.update_values(safe_load_config_options(custom_options_file))

    config_options.update_values(preferred_options)

    return config_options


def safe_load_config_options(options_file: str) -> dict[str, Any]:
    if not options_file:
        print("nothing")
        return None

    logging.info(f"Looking for config options in file: {options_file}")

    options_path = Path(options_file).expanduser()
    if not options_path.is_file() or not options_path.exists():
        print(f"Skipping not a file or doesn't exist: {options_file}")
        logging.info(f"Skipping not a file or doesn't exist: {options_file}")
        return None

    # Let read and parse errors bubble up / blow up the whole thing.
    # Otherwise a pipeline might run with config that wasn't intended.

    with open(options_path) as f:
        options_yaml = f.read()

    options = yaml.safe_load(options_yaml)
    logging.info(f"Found config options in file: {options_file}")

    return options

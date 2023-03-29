from typing import Any, Self
from dataclasses import dataclass, field, fields
from proceed.yaml_data import YamlData


@dataclass
class ConfigOption(YamlData):
    value: Any = None
    cli_long_name: str = None
    cli_short_name: str = None
    cli_nargs: str = None
    cli_type: type = str
    cli_help: str = None
    cli_help_default: str = "%(default)s"

    def cli_help_with_default(self):
        return f"{self.cli_help} (default: {self.cli_help_default})"

    def parse_key_value_pairs(self, delimiter: str = "="):
        key_value_pairs = {}
        if self.value and isinstance(self.value, str):
            for kvp in self.value:
                (k, v) = kvp.split(delimiter)
                key_value_pairs[k] = v
        return key_value_pairs


@dataclass
class ConfigOptions(YamlData):
    """TODO: describe options for sphinx docs"""

    config_files: ConfigOption = field(default_factory=lambda: ConfigOption(
        cli_long_name="--options",
        cli_short_name="-o",
        cli_nargs="*",
        cli_help="YAML file with Proceed config options",
        cli_help_default="user home ~/proceed_options.yaml or current dir ./proceed_options.yaml",
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
        cli_long_name="--args",
        cli_short_name="-a",
        cli_nargs="+",
        cli_help="one or more arg=value assignments to apply to the pipeline, for example: --args foo=bar baz=quux",
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
        value=["sort_keys=False", "default_flow_style=None", "width=1000"],
        cli_long_name="--yaml-options",
        cli_short_name="-y",
        cli_help="one or more key=value assignments to pass as keyword args to PyYAML safe_dump()",
        cli_help_default="-y sort_keys=False default_flow_style=None width=1000",
    ))

    def option_names(self) -> Self:
        return [field.name for field in fields(self)]

    def option(self, option_name) -> ConfigOption:
        return getattr(self, option_name)

    # TODO: from_namespace so we can dump in the argparse results
    # TODO: apply_defaults so we can stack instances from different sources


# TODO: resolve config from multiple sources:
#   hard-coded defaults
#   ~/proceed_config.yaml
#   ./proceed_config.yaml
#   cli --options my_options.yaml

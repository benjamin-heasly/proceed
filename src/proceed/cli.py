import sys
import logging
import yaml
from pathlib import Path
from datetime import datetime, timezone
from argparse import ArgumentParser
from typing import Optional, Sequence
from proceed.model import Pipeline
from proceed.config_options import ConfigOptions, resolve_config_options
from proceed.docker_runner import run_pipeline
from proceed.aggregator import summarize_results
from proceed.__about__ import __version__ as proceed_version

version_string = f"Proceed {proceed_version}"


def set_up_logging(log_file: str = None):
    logging.root.handlers = []
    handlers = [
        logging.StreamHandler(sys.stdout)
    ]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers
    )
    logging.info(version_string)


def run(spec: str, config_options: ConfigOptions) -> int:
    """Execute a pipeline for "proceed run spec ..."""

    if not spec:
        logging.error("You must provide a pipeline spec to the run operation.")
        return -1

    # Choose where to write outputs.
    out_path = Path(config_options.results_dir.value).expanduser()

    if config_options.results_group.value:
        group_path = Path(out_path, config_options.results_group.value)
    else:
        spec_path = Path(spec)
        group_path = Path(out_path, spec_path.stem)

    if config_options.results_id.value:
        execution_path = Path(group_path, config_options.results_id.value)
    else:
        execution_time = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%Z')
        execution_path = Path(group_path, execution_time)

    execution_path.mkdir(parents=True, exist_ok=True)

    # Log to the output path and to the console.
    log_path = Path(execution_path, "proceed.log")
    set_up_logging(log_path)

    logging.info(f"Using output directory: {execution_path.as_posix()}")

    # Record the effective options we're using for this run.
    effective_options_path = Path(execution_path, "effective_options.yaml")
    logging.info(f"Writing effective config options to: {effective_options_path.as_posix()}")
    effective_options_yaml = yaml.safe_dump(config_options.to_dict(), **config_options.yaml_options.value)
    with open(effective_options_path, "w") as f:
        f.write(effective_options_yaml)

    logging.info(f"Parsing pipeline specification from: {spec}")
    with open(spec) as f:
        pipeline = Pipeline.from_yaml(f.read())

    logging.info(f"Running pipeline with args: {config_options.args.value}")
    pipeline_result = run_pipeline(
        original=pipeline,
        execution_path=execution_path,
        args=config_options.args.value,
        force_rerun=config_options.force_rerun.value,
        step_names=config_options.step_names.value)

    record_path = Path(execution_path, "execution_record.yaml")
    logging.info(f"Writing execution record to: {record_path}")
    with open(record_path, "w") as record:
        record.write(pipeline_result.to_yaml(
            skip_empty=config_options.yaml_skip_empty.value,
            dump_args=config_options.yaml_options.value
        ))

    error_count = sum((not not step_result.exit_code) for step_result in pipeline_result.step_results)
    if error_count:
        logging.error(f"{error_count} step(s) had nonzero exit codes:")
        for step_result in pipeline_result.step_results:
            logging.error(f"{step_result.name} exit code: {step_result.exit_code}")
        return error_count
    else:
        logging.info(f"Completed {len(pipeline_result.step_results)} steps successfully.")
        return 0


def summarize(config_options: ConfigOptions) -> int:
    """Collect and organize results for "proceed summarize ..."""

    # Choose where to look for previous results.
    results_path = Path(config_options.results_dir.value)
    logging.info(f"Summarizing results from {results_path.as_posix()}")

    summary = summarize_results(results_path, columns=config_options.summary_columns.value,
                                sort_rows_by=config_options.summary_sort_rows_by.value)

    # Choose where to write the summary of results.
    out_file = Path(config_options.summary_file.value)
    logging.info(f"Writing summary to {out_file.as_posix()}")
    summary.to_csv(out_file)

    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = ArgumentParser(description="Declarative file processing with YAML and containers.")
    parser.add_argument("operation",
                        type=str,
                        choices=["run", "summarize"],
                        help="operation to perform: run a pipeline or summarize results from multiple runs"),
    parser.add_argument("spec",
                        type=str,
                        nargs="?",
                        help="YAML file with pipeline specification to run")
    parser.add_argument("--version", "-v", action="version", version=version_string)

    default_config_options = ConfigOptions()
    for option_name in default_config_options.option_names():
        config_option = default_config_options.config_option(option_name)
        parser.add_argument(
            config_option.cli_long_name,
            config_option.cli_short_name,
            **config_option.cli_kwargs()
        )

    cli_args = parser.parse_args(argv)

    set_up_logging()

    preferred_options = vars(cli_args)
    config_options = resolve_config_options(preferred_options)

    match cli_args.operation:
        case "run":
            exit_code = run(cli_args.spec, config_options)
        case "summarize":
            exit_code = summarize(config_options)
        case _:  # pragma: no cover
            # We don't expect this to happen -- argparse should error before we get here.
            logging.error(f"Unsupported operation: {cli_args.operation}")
            exit_code = -2

    if exit_code:
        logging.error(f"Completed with errors.")
    else:
        logging.info(f"OK.")

    return exit_code

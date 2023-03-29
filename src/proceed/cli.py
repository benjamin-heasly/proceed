import sys
import logging
from pathlib import Path
from datetime import datetime, timezone
from argparse import ArgumentParser, Namespace
from typing import Optional, Sequence
from proceed.model import Pipeline
from proceed.config_options import ConfigOptions
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


def run(cli_args: Namespace) -> int:
    """Execute a pipeline for "proceed run spec ..."""

    if not cli_args.spec:
        logging.error("You must provide a pipeline spec to the run operation.")
        return -1

    # Choose where to write outputs.
    out_path = Path(cli_args.results_dir)

    if cli_args.results_group:
        group_path = Path(out_path, cli_args.results_group)
    else:
        spec_path = Path(cli_args.spec)
        group_path = Path(out_path, spec_path.stem)

    if cli_args.results_id:
        execution_path = Path(group_path, cli_args.results_id)
    else:
        execution_time = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%Z')
        execution_path = Path(group_path, execution_time)

    execution_path.mkdir(parents=True, exist_ok=True)

    # Log to the output path and to the console.
    log_file = Path(execution_path, "proceed.log")
    set_up_logging(log_file)

    # TODO: write the effective config as yaml to the execution dir

    logging.info(f"Using output directory: {execution_path.as_posix()}")

    logging.info(f"Parsing pipeline specification from: {cli_args.spec}")
    with open(cli_args.spec) as spec:
        pipeline = Pipeline.from_yaml(spec.read())

    # TODO: get from config_options.args.parse_key_value_pairs()
    pipeline_args = {}
    if cli_args.args:
        for kvp in cli_args.args:
            (k, v) = kvp.split("=")
            pipeline_args[k] = v

    logging.info(f"Running pipeline with args: {pipeline_args}")
    pipeline_result = run_pipeline(pipeline, execution_path, pipeline_args)

    record_file = Path(execution_path, "execution_record.yaml")
    logging.info(f"Writing execution record to: {record_file}")
    # TODO: get yaml.safe_dump kwargs from config_options.yaml_options.parse_key_value_pairs()
    with open(record_file, "w") as record:
        record.write(pipeline_result.to_yaml(skip_empty=cli_args.yaml_skip_empty))

    error_count = sum((not not step_result.exit_code) for step_result in pipeline_result.step_results)
    if error_count:
        logging.error(f"{error_count} step(s) had nonzero exit codes:")
        for step_result in pipeline_result.step_results:
            logging.error(f"{step_result.name} exit code: {step_result.exit_code}")
        return error_count
    else:
        logging.info(f"Completed {len(pipeline_result.step_results)} steps successfully.")
        return 0


def summarize(cli_args: Namespace) -> int:
    """Collect and organize results for "proceed summarize ..."""

    # Choose where to look for previous results.
    results_path = Path(cli_args.results_dir)
    logging.info(f"Summarizing results from {results_path.as_posix()}")

    summary = summarize_results(results_path, columns=cli_args.summary_columns,
                                sort_rows_by=cli_args.summary_sort_rows_by)

    # Choose where to write the summary of results.
    out_file = Path(cli_args.summary_file)
    logging.info(f"Writing summary to {out_file.as_posix()}")
    summary.to_csv(out_file)

    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = ArgumentParser(description="Declarative file processing with YAML and containers.")
    parser.add_argument("operation",
                        type=str,
                        choices=["run", "summarize"],
                        help="operation to perform: run a pipeline or summarize results from multiple runs."),
    parser.add_argument("spec",
                        type=str,
                        nargs="?",
                        help="YAML file with pipeline specification to run")
    parser.add_argument("--version", "-v", action="version", version=version_string)

    default_config_options = ConfigOptions()
    for option_name in default_config_options.option_names():
        config_option = default_config_options.option(option_name)
        parser.add_argument(
            config_option.cli_long_name,
            config_option.cli_short_name,
            default=config_option.value,
            type=config_option.cli_type,
            nargs=config_option.cli_nargs,
            help=config_option.cli_help_with_default(),
        )

    cli_args = parser.parse_args(argv)

    # TODO: resolve effective config from multiple sources

    set_up_logging()

    # TODO: pass effective config, not cli_args, to operations
    match cli_args.operation:
        case "run":
            exit_code = run(cli_args)
        case "summarize":
            exit_code = summarize(cli_args)
        case _:  # pragma: no cover
            # We don't expect this to happen -- argparse should error before we get here.
            logging.error(f"Unsupported operation: {cli_args.operation}")
            exit_code = -2

    if exit_code:
        logging.error(f"Completed with errors.")
    else:
        logging.info(f"OK.")

    return exit_code

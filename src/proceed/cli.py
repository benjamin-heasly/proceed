import sys
import logging
from pathlib import Path
from datetime import datetime, timezone
import argparse
from typing import Optional, Sequence
from proceed.model import Pipeline
from proceed.docker_runner import run_pipeline
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


def run(cli_args: argparse.Namespace) -> int:
    """Execute a pipeline for "proceed run spec ..."""

    if not cli_args.spec:
        logging.error("You must provide a pipeline spec to the run operation.")
        return -1

    # Choose where to write outputs.
    out_path = Path(cli_args.out_dir)

    if cli_args.out_group:
        group_path = Path(out_path, cli_args.out_group)
    else:
        spec_path = Path(cli_args.spec)
        group_path = Path(out_path, spec_path.stem)

    if cli_args.out_id:
        execution_path = Path(group_path, cli_args.out_id)
    else:
        execution_time = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%Z')
        execution_path = Path(group_path, execution_time)

    execution_path.mkdir(parents=True, exist_ok=True)

    # Log to the output path and to the console.
    log_file = Path(execution_path, "proceed.log")
    set_up_logging(log_file)

    logging.info(f"Using output directory: {execution_path.as_posix()}")

    logging.info(f"Parsing pipeline specification from: {cli_args.spec}")
    with open(cli_args.spec) as spec:
        pipeline = Pipeline.from_yaml(spec.read())

    pipeline_args = {}
    if cli_args.args:
        for kvp in cli_args.args:
            (k, v) = kvp.split("=")
            pipeline_args[k] = v

    logging.info(f"Running pipeline with args: {pipeline_args}")
    pipeline_result = run_pipeline(pipeline, execution_path, pipeline_args)

    record_file = Path(execution_path, "execution_record.yaml")
    logging.info(f"Writing execution record to: {record_file}")
    with open(record_file, "w") as record:
        record.write(pipeline_result.to_yaml(skip_empty=cli_args.skip_empty))

    error_count = sum((not not step_result.exit_code) for step_result in pipeline_result.step_results)
    if error_count:
        logging.error(f"{error_count} step(s) had nonzero exit codes:")
        for step_result in pipeline_result.step_results:
            logging.error(f"{step_result.name} exit code: {step_result.exit_code}")
        return error_count
    else:
        logging.info(f"Completed {len(pipeline_result.step_results)} steps successfully.")
        return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Declarative file processing with YAML and containers.")
    parser.add_argument("operation",
                        type=str,
                        choices=["run", "aggregate"],
                        help="operation to perform: run a pipeline, aggregate results, etc."),
    parser.add_argument("spec",
                        type=str,
                        nargs="?",
                        help="YAML file with pipeline specification to run")
    parser.add_argument("--version", "-v", action="version", version=version_string)
    parser.add_argument("--out-dir", "-o",
                        type=str,
                        help="output directory to receive logs and the execution records (default is ./proceed_out)",
                        default="./proceed_out")
    parser.add_argument("--out-group", "-g",
                        type=str,
                        help="output subdirectory for this pipeline (default is from spec file base name)",
                        default=None)
    parser.add_argument("--out-id", "-i",
                        type=str,
                        help="output subdirectory for this execution (default is from UTC datetime)",
                        default=None)
    parser.add_argument("--skip-empty", "-e",
                        type=bool,
                        help="whether to skip empty lists, empty dicts, and null values when writing the execution record (default is true)",
                        default=True)
    parser.add_argument("--args", "-a",
                        nargs="+",
                        type=str,
                        help="one or more args to pass to the pipeline, for example: --args foo=bar baz=quux")
    cli_args = parser.parse_args(argv)

    set_up_logging()

    match cli_args.operation:
        case "run":
            exit_code = run(cli_args)
        case "aggregate":
            exit_code = 0
        case _: # pragma: no cover
            # We don't expect this to happen -- argparse should error before we get here.
            logging.error(f"Unsupported operation: {cli_args.operation}")
            exit_code = -2

    if exit_code:
        logging.error(f"Completed with errors.")
    else:
        logging.info(f"OK.")

    return exit_code

import sys
import logging
from pathlib import Path
from datetime import datetime, timezone
import argparse
from typing import Optional, Sequence
from proceed.model import Pipeline
from proceed.docker_runner import run_pipeline


def set_up_logging(log_file: str, spec_file: str):
    if not log_file:
        log_suffix = datetime.now(timezone.utc).isoformat(sep="T")
        spec_path = Path(spec_file)
        log_file = f"{spec_path.stem}_{log_suffix}.log"

    logging.root.handlers = []
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Declarative file processing with YAML and containers.")
    parser.add_argument("spec",
                        type=str,
                        help="input file with proceed pipeline specification (YAML)")
    parser.add_argument("--record", "-r",
                        type=str,
                        help="output file to receive pipeline execution record (YAML)",
                        default="execution_record.yml")
    parser.add_argument("--skip-empty", "-s",
                        type=bool,
                        help="whether to skip empty lists and dicts and null values when writing the execution record",
                        default=True)
    parser.add_argument("--log-file", "-l",
                        type=str,
                        help="output file to receive runtime log (default chosen based on pipeline spec and datetime)",
                        default=None)
    parser.add_argument("--args", "-a",
                        nargs="+",
                        type=str,
                        help="one or more args to pass to the pipeline, for example: --args foo=bar baz=quux")
    cli_args = parser.parse_args(argv)

    set_up_logging(cli_args.log_file, cli_args.spec)

    logging.info(f"Parsing proceed pipeline specification from: {cli_args.spec}")

    with open(cli_args.spec) as spec:
        pipeline = Pipeline.from_yaml(spec.read())

    pipeline_args = {}
    if cli_args.args:
        for kvp in cli_args.args:
            (k, v) = kvp.split("=")
            pipeline_args[k] = v

    logging.info(f"Running pipeline with args: {pipeline_args}")

    pipeline_result = run_pipeline(pipeline, pipeline_args)

    logging.info(f"Writing execution record to: {cli_args.record}")

    with open(cli_args.record, "w") as record:
        record.write(pipeline_result.to_yaml(skip_empty=cli_args.skip_empty))

    error_count = sum((not not step_result.exit_code) for step_result in pipeline_result.step_results)
    if error_count:
        logging.info(f"{error_count} step(s) had nonzero exit codes:")
        for step_result in pipeline_result.step_results:
            logging.info(f"{step_result.name} exit code: {step_result.exit_code}")
        logging.info(f"Completed with errors.")
        return error_count
    else:
        logging.info(f"OK.")
        return 0

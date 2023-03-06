import argparse
from typing import Optional, Sequence
from proceed.model import Pipeline
from proceed.docker_runner import run_pipeline


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Declarative file processing with YAML and containers.")
    parser.add_argument("spec",
                        type=str,
                        help="input file with proceed pipeline specification")
    parser.add_argument("--record", "-r",
                        type=str,
                        help="output file to receive execution record",
                        default="execution_record.yml")
    parser.add_argument("--args", "-a",
                        nargs="+",
                        type=str,
                        help="one or more args to pass to the pipeline, for example: --args foo=bar baz=quux")
    parser.add_argument("--working_dir", "-w",
                        type=str,
                        help="working dir for the pipeline run",
                        default=".")
    cli_args = parser.parse_args(argv)

    print(f"Parsing proceed pipeline specification from: {cli_args.spec}")

    with open(cli_args.spec) as spec:
        pipeline = Pipeline.from_yaml(spec.read())

    pipeline_args = {}
    if cli_args.args:
        for kvp in cli_args.args:
            (k, v) = kvp.split("=")
            pipeline_args[k] = v

    print(f"Running pipeline with args: {pipeline_args}")

    pipeline_result = run_pipeline(pipeline, pipeline_args, cli_args.working_dir)

    print(f"Writing execution record to: {cli_args.record}")

    with open(cli_args.record, "w") as record:
        record.write(pipeline_result.to_yaml())

    error_count = sum(step_result.exit_code != 0 for step_result in pipeline_result.step_results)
    if error_count:
        print(f"{error_count} steps had nonzero exit codes:")
        for step_result in pipeline_result.step_results:
            print(f"{step_result.name} exit code: {step_result.exit_code}")
        return error_count
    else:
        print(f"OK.")
        return 0

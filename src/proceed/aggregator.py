import logging
from typing import Any
from pathlib import Path
from pandas import DataFrame
import yaml
from proceed.model import ExecutionRecord, Pipeline, Step, Timing, StepResult
from proceed.file_matching import flatten_matches, file_summary, hash_contents

def summarize_results(results_path: Path, columns: list[str] = None, sort_rows_by: list[str] = None) -> DataFrame:
    summary_rows = []
    group_paths = [path for path in results_path.iterdir() if path.is_dir()]
    for group_path in group_paths:
        id_paths = [path for path in group_path.iterdir() if path.is_dir()]
        for id_path in id_paths:
            for yaml_file in id_path.glob("execution_record.yaml"):
                execution_record = safe_read_execution_record(yaml_file)
                if execution_record:
                    execution_summary = summarize_execution(id_path.stem, group_path.stem, execution_record)
                    summary_rows = summary_rows + execution_summary

    summary = DataFrame(summary_rows)

    if columns:
        summary_columns = list(summary.columns)
        usable_columns = [column for column in columns if column in summary_columns]
        summary = summary.filter(items=columns)

    if sort_rows_by:
        summary_columns = list(summary.columns)
        usable_columns = [column for column in sort_rows_by if column in summary_columns]
        summary = summary.sort_values(usable_columns)

    return summary


def safe_read_execution_record(yaml_file: Path) -> ExecutionRecord:
    try:
        with open(yaml_file) as f:
            return ExecutionRecord.from_yaml(f.read())
    except:
        logging.error(f"Skipping file that seems not to be a Proceed execution record: {yaml_file}")
        return None


def summarize_execution(results_id: str, group: str, execution_record: ExecutionRecord) -> list[dict[str, str]]:
    pipeline_summary = summarize_pipeline(results_id, group, execution_record.amended, execution_record.timing)

    steps_and_results = zip(execution_record.amended.steps, execution_record.step_results)
    step_summaries = [summarize_step_and_result(step, result) for step, result in steps_and_results]

    combined_summary = [{**pipeline_summary, **file_summary} for step_summary in step_summaries for file_summary in step_summary]
    return combined_summary


def summarize_pipeline(results_id: str, group: str, pipeline: Pipeline, timing: Timing) -> dict[str, str]:
    top_level_summary = {
        "proceed_version": pipeline.version,
        "results_id": results_id,
        "results_group": group,
        "pipeline_description": pipeline.description,
        "pipeline_start": timing.start,
        "pipeline_finish": timing.finish,
        "pipeline_duration": timing.duration,
    }

    arg_summary = {f"arg_{key}": value for key, value in pipeline.args.items()}

    combined_summary = {**top_level_summary, **arg_summary}
    return combined_summary


def summarize_step_and_result(step: Step, result: StepResult) -> list[dict[str, Any]]:
    step_summary = {f"step_{key}": str(value) for key, value in step.to_dict().items()}

    flattened_step_attributes = {"timing", "log_file", "files_done", "files_in", "files_out", "files_summary"}
    result_summary = {f"step_{key}": str(value) for key, value in result.to_dict().items() if key not in flattened_step_attributes}

    result_summary["step_start"] = result.timing.start
    result_summary["step_finish"] = result.timing.finish
    result_summary["step_duration"] = result.timing.duration

    if result.log_file:
        log_path = Path(result.log_file)
        log_digest = hash_contents(log_path)
        log_file = file_summary(volume=log_path.parent.as_posix(), path=log_path.name, digest=log_digest, file_role="log")
    else:
        log_file = file_summary(volume="", path="", digest="", file_role="log")

    done_files = flatten_matches(result.files_done, file_role="done")
    in_files = flatten_matches(result.files_in, file_role="in")
    out_files = flatten_matches(result.files_out, file_role="out")
    summary_files = flatten_matches(result.files_summary, file_role="summary")

    all_files = [log_file] + done_files + in_files + out_files + summary_files

    custom_summary = {}
    for summary_file in summary_files:
        custom_columns = collect_custom_columns(summary_file["file_volume"], summary_file["file_path"])
        custom_summary.update(custom_columns)

    combined_summary = [{**step_summary, **result_summary, **file_summary, **custom_summary} for file_summary in all_files]
    return combined_summary


def collect_custom_columns(file_volume: str, file_path: str) -> dict[str, str]:
    path = Path(file_volume, file_path)
    if not path.is_file() or not path.exists():
        return {}

    with open(path) as f:
        content = f.read()

    try:
        parsed = yaml.safe_load(content)
        if parsed and isinstance(parsed, dict):
            return parsed

        logging.info(f"Treating non-dictionary YAML as plain text: {path.as_posix()}")

    except yaml.parser.ParserError:
        logging.info(f"Treating non-YAML file as plain text: {path.as_posix()}")

    return {path.stem: content.strip()}

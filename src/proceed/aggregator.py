import logging
from typing import Any
from pathlib import Path
from pandas import DataFrame
from proceed.model import ExecutionRecord, Pipeline, Step, Timing, StepResult
from proceed.file_matching import flatten_matches, file_summary, hash_contents


def summarize_results(results_path: Path) -> dict[str, str]:
    summary = []
    for group_path in results_path.iterdir():
        for id_path in group_path.iterdir():
            for yaml_file in id_path.glob("*.y*ml"):
                execution_record = safe_read_execution_record(yaml_file)
                if execution_record:
                    execution_summary = summarize_execution(id_path.stem, group_path.stem, execution_record)
                    summary = summary + execution_summary
    # TODO: let user pick columns and ordering (don't blow up if missing for some executions!)
    return DataFrame(summary).sort_values(['results_group', 'results_id', 'pipeline_start'])


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

    special_result_fields = ["timing", "log_file", "files_done", "files_in", "files_out"]
    result_summary = {f"step_{key}": str(value) for key, value in result.to_dict().items() if key not in special_result_fields}

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

    all_files = [log_file] + done_files + in_files + out_files

    combined_summary = [{**step_summary, **result_summary, **file_summary} for file_summary in all_files]
    return combined_summary

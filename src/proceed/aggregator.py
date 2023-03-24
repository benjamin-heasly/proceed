import logging
from typing import Any
from pathlib import Path
from pandas import DataFrame
from proceed.model import ExecutionRecord, StepResult
from proceed.file_matching import flatten_matches


def summarize_results(results_path: Path) -> dict[str, str]:
    summary = []
    for group_path in results_path.iterdir():
        for id_path in group_path.iterdir():
            for yaml_file in id_path.glob("*.y*ml"):
                execution_record = safe_read_execution_record(yaml_file)
                if execution_record:
                    for step_result in execution_record.step_results:
                        step_summary = summarize_step(id_path.stem, group_path.stem, step_result)
                        summary = summary + step_summary
    return DataFrame(summary).sort_values(['group', 'run_id', 'start'])


def safe_read_execution_record(yaml_file: Path) -> ExecutionRecord:
    try:
        with open(yaml_file) as f:
            return ExecutionRecord.from_yaml(f.read())
    except:
        logging.error(f"Skipping file that seems not to be a Proceed execution record: {yaml_file}")
        return None


def summarize_step(id: str, group: str, step_result: StepResult) -> list[dict[str, Any]]:
    # use standard/automatable names with a view to dynamic column choices
    step_summary = {
        "group": group,
        "run_id": id,
        "step_name": step_result.name,
        "exit_code": step_result.exit_code,
        "skipped": step_result.skipped,
        "start": step_result.timing.start,
        "finish": step_result.timing.finish,
        "duration": step_result.timing.duration,
        "image_id": step_result.image_id,
    }

    files_done = summarize_file_matches("files_done", step_result.files_done)
    files_in = summarize_file_matches("files_in", step_result.files_in)
    files_out = summarize_file_matches("files_out", step_result.files_out)
    file_summaries = files_done + files_in + files_out

    # TODO include log to guarantee at least one file per step result

    # TODO join step results and corresponding steps
    # TODO include step args as columns with amended values as values

    if not file_summaries:
        return [step_summary]

    combined_summary = [{**step_summary, **file_summary} for file_summary in file_summaries]
    return combined_summary


def summarize_file_matches(label: str, matches: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    flattened = flatten_matches(matches)
    files_summary = [{"label": label, "path": path, "digest": digest} for path, digest in flattened]
    return files_summary

import logging
from pathlib import Path
from pandas import DataFrame, concat
from proceed.model import ExecutionRecord, StepResult


def aggregate_results(results_path: Path) -> dict[str, str]:
    summary = []
    for group_path in results_path.iterdir():
        for id_path in group_path.iterdir():
            for yaml_file in id_path.glob("*.y*ml"):
                execution_record = safe_read_execution_record(yaml_file)
                if execution_record:
                    for step_result in execution_record.step_results:
                        step_summary = summarize(id_path.stem, group_path.stem, step_result)
                        summary.append(step_summary)
    return DataFrame(summary).sort_values(['group', 'id', 'start'])


def safe_read_execution_record(yaml_file: Path) -> ExecutionRecord:
    try:
        with open(yaml_file) as f:
            return ExecutionRecord.from_yaml(f.read())
    except Exception as e:
        logging.error(f"File {yaml_file} seems not to be a Proceed execution record: {e.args}")
        return None


def summarize(id: str, group: str, step_result: StepResult):
    step_summary = {
        "group": group,
        "id": id,
        "step_name": step_result.name,
        "image_id": step_result.image_id,
        "skipped": step_result.skipped,
        "exit_code": step_result.exit_code,
        "start": step_result.timing.start,
        "finish": step_result.timing.finish,
        "duration": step_result.timing.duration
    }

    # TODO: include info from the original amended args and/or steps?

    # TODO: how to represent collections in an easy-to-audit way?
    # step_results: files_done, files_in, files_out

    return step_summary

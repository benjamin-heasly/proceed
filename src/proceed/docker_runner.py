import logging
from typing import Union
from datetime import datetime, timezone
from pathlib import Path
import docker
from proceed.model import Pipeline, ExecutionRecord, Step, StepResult, Timing
from proceed.file_matching import count_matches, match_patterns_in_dirs


def run_pipeline(original: Pipeline, execution_path: Path, args: dict[str, str] = {}) -> ExecutionRecord:
    """
    Run a pipeline with all its steps and return results.

    :param original: a Pipeline, as read from an input YAML spec
    :return: a summary of Pipeline execution results.

    """

    logging.info("Starting pipeline run.")

    start = datetime.now(timezone.utc)

    amended = original._with_args_applied(args)._with_prototype_applied()
    step_results = []
    for step in amended.steps:
        log_stem = step.name.replace(" ", "_")
        log_path = Path(execution_path, f"{log_stem}.log")
        step_result = run_step(step, log_path)
        step_results.append(step_result)
        if step_result.exit_code:
            logging.error("Stopping pipeline run after error.")
            break

    finish = datetime.now(timezone.utc)
    duration = finish - start

    logging.info("Finished pipeline run.")

    return ExecutionRecord(
        original=original,
        amended=amended,
        step_results=step_results,
        timing=Timing(start.isoformat(sep="T"), finish.isoformat(sep="T"), duration.total_seconds())
    )


def run_step(step: Step, log_path: Path) -> StepResult:
    logging.info(f"Step '{step.name}': starting.")

    start = datetime.now(timezone.utc)

    volume_dirs = step.volumes.keys()
    files_done = match_patterns_in_dirs(volume_dirs, step.match_done)
    if files_done:
        logging.info(f"Step '{step.name}': found {count_matches(files_done)} done files, skipping execution.")
        return StepResult(
            name=step.name,
            skipped=True,
            files_done=files_done,
            timing=Timing(start.isoformat(sep="T"))
        )

    files_in = match_patterns_in_dirs(volume_dirs, step.match_in)
    logging.info(f"Step '{step.name}': found {count_matches(files_in)} input files.")

    device_requests = []
    if step.gpus:
        device_requests.append(docker.types.DeviceRequest(count=-1, capabilities=[["gpu"]]))

    client = docker.from_env()
    try:
        container = client.containers.run(
            step.image,
            command=step.command,
            environment=step.environment,
            device_requests=device_requests,
            network_mode=step.network_mode,
            mac_address=step.mac_address,
            volumes=volumes_to_absolute_host(volumes_to_dictionaries(step.volumes)),
            working_dir=step.working_dir,
            auto_remove=False,
            remove=False,
            detach=True
        )
        logging.info(f"Step '{step.name}': waiting for process to complete.")

        # Tail the container logs and write new lines to the step log and the proceed log as they arrive.
        step_log_stream = container.logs(stdout=True, stderr=True, stream=True)
        with open(log_path, 'w') as f:
            for log_entry in step_log_stream:
                log = log_entry.decode("utf-8")
                f.write(log)
                logging.info(f"Step '{step.name}': {log}")

        # Collect overall logs and status of the finished procedss.
        run_results = container.wait()
        step_exit_code = run_results['StatusCode']
        logging.info(f"Step '{step.name}': process completed with exit code {step_exit_code}")

        container.remove()

        files_out = match_patterns_in_dirs(volume_dirs, step.match_out)
        logging.info(f"Step '{step.name}': found {count_matches(files_out)} output files.")

        files_summary = match_patterns_in_dirs(volume_dirs, step.match_summary)
        logging.info(f"Step '{step.name}': found {count_matches(files_summary)} summary files.")

        finish = datetime.now(timezone.utc)
        duration = finish - start

        logging.info(f"Step '{step.name}': finished.")

        return StepResult(
            name=step.name,
            image_id=container.image.id,
            exit_code=step_exit_code,
            log_file=log_path.as_posix(),
            files_done=files_done,
            files_in=files_in,
            files_out=files_out,
            files_summary=files_summary,
            timing=Timing(start.isoformat(sep="T"), finish.isoformat(sep="T"), duration.total_seconds()),
        )

    except docker.errors.ImageNotFound as image_not_found_error:
        error_message = image_not_found_error.explanation
        with open(log_path, 'w') as f:
            f.write(error_message)

        logging.error(f"Step '{step.name}': ImageNotFound error --\n {error_message}")
        return StepResult(
            name=step.name,
            log_file=log_path.as_posix(),
            timing=Timing(start.isoformat(sep="T"))
        )

    except docker.errors.APIError as api_error:
        error_message = api_error.explanation
        with open(log_path, 'w') as f:
            f.write(error_message)

        logging.error(f"Step '{step.name}': APIError error --\n {error_message}")
        return StepResult(
            name=step.name,
            log_file=log_path.as_posix(),
            timing=Timing(start.isoformat(sep="T"))
        )

    except OSError as os_error: # pragma: no cover
        # This is a fallback for really unexpected errors calling Docker,
        # for example: https://github.com/docker/for-win/issues/13324
        # I don't know a good way to induce this case in tests, hence the "no cover"
        error_message = f"errno {os_error.errno}: {os_error.strerror} {os_error.filename}"
        with open(log_path, 'w') as f:
            f.write(error_message)

        logging.error(f"Step '{step.name}': OSError error --\n {error_message}")
        return StepResult(
            name=step.name,
            log_file=log_path.as_posix(),
            timing=Timing(start.isoformat(sep="T"))
        )


def volumes_to_dictionaries(volumes: dict[str, Union[str, dict[str, str]]],
                            default_mode: str = "rw") -> dict[str, dict[str, str]]:
    normalized = {}
    for k, v in volumes.items():
        if isinstance(v, str):
            normalized[k] = {"bind": v, "mode": default_mode}
        else:
            normalized[k] = v
    return normalized


def volumes_to_absolute_host(volumes: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    absolute = {Path(k).absolute().as_posix(): v for k, v in volumes.items()}
    return absolute

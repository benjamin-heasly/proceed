import logging
from typing import Union
from datetime import datetime, timezone
from pathlib import Path
import docker
from proceed.model import Pipeline, PipelineResult, Step, StepResult, Timing
from proceed.file_matching import count_matches, match_patterns_in_dirs


def run_pipeline(original: Pipeline, args: dict[str, str] = {}) -> PipelineResult:
    logging.info("Starting pipeline run.")

    start = datetime.now(timezone.utc)

    amended = original.with_args_applied(args).with_prototype_applied()
    step_results = []
    for step in amended.steps:
        step_result = run_step(step)
        step_results.append(step_result)
        if step_result.exit_code:
            logging.info("Stopping pipeline run after error.")
            break

    finish = datetime.now(timezone.utc)
    duration = finish - start

    logging.info("Finished pipeline run.")

    return PipelineResult(
        original=original,
        amended=amended,
        step_results=step_results,
        timing=Timing(start.isoformat(sep="T"), finish.isoformat(sep="T"), duration.total_seconds())
    )


def run_step(step: Step) -> StepResult:
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
            timing=Timing(str(start))
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
        run_results = container.wait()
        step_exit_code=run_results['StatusCode']
        logging.info(f"Step '{step.name}': process completed with exit code {step_exit_code}")

        # Retrieve container logs before removing the container.
        # The sdk has a race condition around this, otherwise we could just do:
        # log_bytes = client.containers.run( ... detach=False, remove=True)
        logs = container.logs().decode("utf-8")
        container.remove()

        if step_exit_code:
            logging.info(f"Step '{step.name}': logs --\n {logs}")

        files_out = match_patterns_in_dirs(volume_dirs, step.match_out)
        logging.info(f"Step '{step.name}': found {count_matches(files_out)} output files.")

        finish = datetime.now(timezone.utc)
        duration = finish - start

        logging.info(f"Step '{step.name}': finished.")

        return StepResult(
            name=step.name,
            image_id=container.image.id,
            exit_code=step_exit_code,
            logs=logs,
            files_done=files_done,
            files_in=files_in,
            files_out=files_out,
            timing=Timing(start.isoformat(sep="T"), finish.isoformat(sep="T"), duration.total_seconds())
        )

    except docker.errors.ImageNotFound as image_not_found_error:
        logging.info(f"Step '{step.name}': error --\n {image_not_found_error.explanation}")
        return StepResult(
            name=step.name,
            logs=image_not_found_error.explanation,
            timing=Timing(start.isoformat(sep="T"))
        )

    except docker.errors.APIError as api_error:
        logging.info(f"Step '{step.name}': error --\n {api_error.explanation}")
        return StepResult(
            name=step.name,
            logs=api_error.explanation,
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

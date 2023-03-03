from typing import Union
from datetime import datetime, timezone
import docker
from proceed.model import Pipeline, PipelineResult, Step, StepResult, Timing


def run_pipeline(original: Pipeline, args: dict[str, str] = {}) -> PipelineResult:
    start = datetime.now(timezone.utc)

    amended = original.with_args_applied(args)
    step_results = [run_step(step, amended.volumes) for step in amended.steps]

    finish = datetime.now(timezone.utc)
    duration = finish - start

    return PipelineResult(
        original=original,
        amended=amended,
        step_results=step_results,
        timing=Timing(str(start), str(finish), duration.total_seconds())
    )


def run_step(step: Step, volumes: dict[str, Union[str, dict[str, str]]] = {}) -> StepResult:
    start = datetime.now(timezone.utc)

    combined_volumes = volumes_to_dictionaries({**volumes, **step.volumes})

    client = docker.from_env()
    try:
        container = client.containers.run(
            step.image,
            command=step.command,
            volumes=combined_volumes,
            auto_remove=False,
            remove=False,
            detach=True
        )
        run_results = container.wait()

        # Retrieve container logs before removing the container.
        # The sdk has a race condition around this, otherwise we could just do:
        # log_bytes = client.containers.run( ... detach=False, remove=True)
        logs = container.logs().decode("utf-8")
        container.remove()

        finish = datetime.now(timezone.utc)
        duration = finish - start

        return StepResult(
            name=step.name,
            image_id=container.image.id,
            exit_code=run_results['StatusCode'],
            logs=logs,
            timing=Timing(str(start), str(finish), duration.total_seconds())
        )

    except docker.errors.ImageNotFound as image_not_found_error:
        return StepResult(
            name=step.name,
            logs=image_not_found_error.explanation,
            timing=Timing(str(start))
        )

    except docker.errors.APIError as api_error:
        return StepResult(
            name=step.name,
            logs=api_error.explanation,
            timing=Timing(str(start))
        )


def volumes_to_dictionaries(volumes: dict[str, Union[str, dict[str, str]]],
                            default_mode: str = "rw") -> dict[str, dict[str, str]]:
    normalized = {}
    for k in volumes.keys():
        v = volumes[k]
        if isinstance(v, str):
            normalized[k] = {"bind": v, "mode": default_mode}
        else:
            normalized[k] = v
    return normalized

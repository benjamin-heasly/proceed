from typing import Union
import docker
from proceed.model import Pipeline, PipelineResult, Step, StepResult


def run_pipeline(original: Pipeline, args: dict[str, str] = {}) -> PipelineResult:
    amended = original.with_args_applied(args)
    step_results = [run_step(step, amended.volumes) for step in amended.steps]
    return PipelineResult(
        original=original,
        amended=amended,
        step_results=step_results
    )


def run_step(step: Step, volumes: dict[str, Union[str, dict[str, str]]] = {}) -> StepResult:
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
        return StepResult(
            name=step.name,
            image_id=container.image.id,
            exit_code=run_results['StatusCode'],
            logs=logs
        )

    except docker.errors.ImageNotFound as image_error:
        return StepResult(
            name=step.name,
            logs=image_error.value.explanation
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

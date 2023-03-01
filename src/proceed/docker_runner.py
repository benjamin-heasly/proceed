from typing import Union
import docker
from proceed.model import Pipeline, PipelineResult, Step, StepResult


def run_pipeline(original: Pipeline, args: dict[str, str] = {}) -> PipelineResult:
    applied = original.with_args_applied(args)
    step_results = [run_step(step, applied.volumes) for step in applied.steps]
    return PipelineResult(
        original=original,
        applied=applied,
        step_results=step_results
    )


def run_step(step: Step, volumes: dict[str, Union[str, dict[str, str]]] = {}) -> StepResult:
    combined_volumes = volumes_to_dictionaries({**volumes, **step.volumes})
    print(combined_volumes)
    client = docker.from_env()
    try:
        log_bytes = client.containers.run(
            step.image,
            volumes=combined_volumes,
            command=step.command
        )
        return StepResult(
            name=step.name,
            image_id=client.images.get(step.image).id,
            exit_code=0,
            logs=log_bytes.decode("utf-8")
        )

    except docker.errors.ContainerError as container_error:
        log_bytes = container_error.container.logs()
        return StepResult(
            name=step.name,
            exit_code=container_error.exit_status,
            logs=log_bytes.decode("utf-8")
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

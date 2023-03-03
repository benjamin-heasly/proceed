from typing import Union
from datetime import datetime, timezone
import docker
from proceed.model import Pipeline, PipelineResult, Step, StepResult, Timing


def run_pipeline(original: Pipeline, args: dict[str, str] = {}) -> PipelineResult:
    start = datetime.now(timezone.utc)

    amended = original.with_args_applied(args)
    step_results = [
        run_step(
            step,
            environment=amended.environment,
            network_mode=amended.network_mode,
            mac_address=amended.mac_address,
            volumes=amended.volumes
        )
        for step in amended.steps
    ]

    finish = datetime.now(timezone.utc)
    duration = finish - start

    return PipelineResult(
        original=original,
        amended=amended,
        step_results=step_results,
        timing=Timing(str(start), str(finish), duration.total_seconds())
    )


def run_step(step: Step,
             environment: dict[str, str] = {},
             network_mode: str = None,
             mac_address: str = None,
             volumes: dict[str, Union[str, dict[str, str]]] = {}
             ) -> StepResult:
    start = datetime.now(timezone.utc)

    combined_environment = {**environment, **step.environment}
    effective_network_mode = step.network_mode or network_mode
    effective_mac_address = step.mac_address or mac_address
    combined_volumes = volumes_to_dictionaries({**volumes, **step.volumes})

    device_requests = []
    if step.gpus:
        device_requests.append(docker.types.DeviceRequest(count=-1, capabilities=[["gpu"]]))

    client = docker.from_env()
    try:
        container = client.containers.run(
            step.image,
            command=step.command,
            environment=combined_environment,
            device_requests=device_requests,
            network_mode=effective_network_mode,
            mac_address=effective_mac_address,
            volumes=combined_volumes,
            working_dir=step.working_dir,
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

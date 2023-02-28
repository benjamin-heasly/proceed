import docker
from pipeline_stuff.model import Pipeline, PipelineResult, Step, StepResult


def run_pipeline(original: Pipeline) -> PipelineResult:
    applied = original.with_args_applied(original.args)
    step_results = [run_step(step) for step in applied.steps]
    return PipelineResult(
        original=original,
        applied=applied,
        step_results=step_results
    )


def run_step(step: Step) -> StepResult:
    client = docker.from_env()
    try:
        log_bytes = client.containers.run(
            step.image,
            volumes=step.volumes,
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

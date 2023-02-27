import docker
from pipeline_stuff.model import Pipeline, PipelineResult, Step, StepResult


def run_pipeline(pipeline: Pipeline) -> PipelineResult:
    step_results = [run_step(step) for step in pipeline.steps]
    return PipelineResult(pipeline, step_results)


def run_step(step: Step) -> StepResult:
    client = docker.from_env()
    try:
        log_bytes = client.containers.run(
            step.image,
            volumes=step.volumes,
            command=step.command
        )
        return StepResult(0, log_bytes.decode("utf-8"))

    except docker.errors.ContainerError as container_error:
        log_bytes = container_error.container.logs()
        return StepResult(container_error.exit_status, log_bytes.decode("utf-8"))

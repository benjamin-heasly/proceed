import docker
from pytest import fixture
from proceed.model import Pipeline, PipelineResult, Step, StepResult
from proceed.docker_runner import run_pipeline, run_step


@fixture
def alpine_image():
    """The alpine image must be present on the host, and/or we must be on the network."""
    client = docker.from_env()
    image = client.images.pull("alpine")
    return image


def test_step_image_not_found():
    step = Step(name="image not found", image="no_such_image")
    step_result = run_step(step)
    assert step_result.name == step.name
    assert step_result.image_id == None
    assert step_result.exit_code == None
    assert "no_such_image, repository does not exist" in step_result.logs


def test_step_command_not_found(alpine_image):
    step = Step(name="command not found", image=alpine_image.tags[0], command="no_such_command")
    step_result = run_step(step)
    assert step_result.name == step.name
    assert step_result.image_id == None
    assert step_result.exit_code == None
    assert '"no_such_command": executable file not found' in step_result.logs


def test_step_command_error(alpine_image):
    step = Step(name="command error", image=alpine_image.tags[0], command="ls no_such_dir")
    step_result = run_step(step)
    assert step_result.name == step.name
    assert step_result.image_id == alpine_image.id
    assert step_result.exit_code == 1
    assert "no_such_dir: No such file or directory" in step_result.logs


def test_step_command_success(alpine_image):
    step = Step(name="command success", image=alpine_image.tags[0], command="echo 'hello to you'")
    step_result = run_step(step)
    assert step_result.name == step.name
    assert step_result.image_id == alpine_image.id
    assert step_result.exit_code == 0
    assert "hello to you" in step_result.logs


def test_step_working_dir(alpine_image):
    step = Step(name="working dir", working_dir="/home", image=alpine_image.tags[0], command="pwd")
    step_result = run_step(step)
    assert step_result.name == step.name
    assert step_result.image_id == alpine_image.id
    assert step_result.exit_code == 0
    assert step_result.logs == "/home\n"


def test_pipeline_with_args(alpine_image):
    pipeline = Pipeline(
        args={
            "arg_1": "foo",
            "arg_2": "bar"
        },
        steps=[
            Step(name="step 1", image=alpine_image.tags[0], command="echo 'hello $arg_1'"),
            Step(name="step 2", image=alpine_image.tags[0], command="echo 'hello $arg_2'")
        ]
    )
    args = {
        "ignored": "ignore me",
        "arg_1": "quux"
    }
    pipeline_result = run_pipeline(pipeline, args)
    expected_amended = Pipeline(
        args={
            "arg_1": "quux",
            "arg_2": "bar"
        },
        steps=[
            Step(name="step 1", image=alpine_image.tags[0], command="echo 'hello quux'"),
            Step(name="step 2", image=alpine_image.tags[0], command="echo 'hello bar'")
        ]
    )
    expected_step_results = [
        StepResult(name="step 1", image_id=alpine_image.id, exit_code=0, logs="hello quux\n"),
        StepResult(name="step 2", image_id=alpine_image.id, exit_code=0, logs="hello bar\n")
    ]
    expected_result = PipelineResult(
        original=pipeline,
        amended=expected_amended,
        step_results=expected_step_results
    )
    assert pipeline_result == expected_result

    # Timing details are not used in comparisons above, that would be too brittle.
    # But we do want to check that timing results got filled in.
    assert pipeline_result.timing.is_complete()
    assert all([step_result.timing.is_complete() for step_result in pipeline_result.step_results])

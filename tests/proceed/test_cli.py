import docker
from pathlib import Path
from pytest import fixture, raises
from proceed.cli import main
from proceed.model import Pipeline, PipelineResult, StepResult

@fixture
def alpine_image():
    """The alpine image must be present on the host, and/or we must be on the network."""
    client = docker.from_env()
    image = client.images.pull("alpine")
    return image


@fixture
def fixture_path(request):
    this_file = Path(request.module.__file__)
    return Path(this_file.parent, 'fixture_files')


@fixture
def fixture_files(fixture_path):
    yaml_files = fixture_path.glob("*.yaml")
    return {yaml_file.name: yaml_file for yaml_file in yaml_files}


def test_happy_pipeline(fixture_files, tmp_path, alpine_image):
    pipeline_spec = fixture_files['happy_spec.yaml'].as_posix()
    record_file = Path(tmp_path, 'happy_record.yaml').as_posix()
    cli_args = [pipeline_spec, '--record', record_file, '--args', 'arg_1=quux']
    exit_code = main(cli_args)
    assert exit_code == 0

    with open(pipeline_spec) as f:
        original = Pipeline.from_yaml(f.read())

    expected_result = PipelineResult(
        original=original,
        amended=original.with_args_applied({"arg_1": "quux"}),
        step_results=[
            StepResult(name="hello", exit_code=0, image_id=alpine_image.id, logs="quux\n")
        ]
    )

    with open(record_file) as f:
        pipeline_result = PipelineResult.from_yaml(f.read())

    assert pipeline_result == expected_result


def test_sad_pipeline(fixture_files, tmp_path, alpine_image):
    pipeline_spec = fixture_files['sad_spec.yaml'].as_posix()
    record_file = Path(tmp_path, 'sad_record.yaml').as_posix()
    cli_args = [pipeline_spec, '--record', record_file]
    exit_code = main(cli_args)
    assert exit_code == 1

    with open(pipeline_spec) as f:
        original = Pipeline.from_yaml(f.read())

    expected_result = PipelineResult(
        original=original,
        amended=original,
        step_results=[
            StepResult(name="bad", exit_code=1, image_id=alpine_image.id, logs="ls: no_such_dir: No such file or directory\n")
        ]
    )

    with open(record_file) as f:
        pipeline_result = PipelineResult.from_yaml(f.read())

    assert pipeline_result == expected_result


def test_help():
    with raises(SystemExit) as exception_info:
        main(["--help"])
    assert 0 in exception_info.value.args


def test_invalid_input():
    with raises(FileNotFoundError) as exception_info:
        main(["no_such_file"])
    assert 2 in exception_info.value.args

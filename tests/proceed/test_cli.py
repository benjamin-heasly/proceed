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
    cli_args = [pipeline_spec, '--out-dir', tmp_path.as_posix(), '--out-id', "test", '--args', 'arg_1=quux']
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

    with open(Path(tmp_path, "happy_spec", "test", "execution_record.yaml")) as f:
        pipeline_result = PipelineResult.from_yaml(f.read())

    assert pipeline_result == expected_result

    with open(Path(tmp_path, "happy_spec", "test", "proceed.log")) as f:
        log = f.read()

    assert "Parsing proceed pipeline specification" in log
    assert log.endswith("OK.\n")


def test_sad_pipeline(fixture_files, tmp_path, alpine_image):
    pipeline_spec = fixture_files['sad_spec.yaml'].as_posix()
    cli_args = [pipeline_spec, '--out-dir', tmp_path.as_posix(), '--out-id', "test", '--args', 'arg_1=quux']
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

    with open(Path(tmp_path, "sad_spec", "test", "execution_record.yaml")) as f:
        pipeline_result = PipelineResult.from_yaml(f.read())

    assert pipeline_result == expected_result

    with open(Path(tmp_path, "sad_spec", "test", "proceed.log")) as f:
        log = f.read()

    assert "Parsing proceed pipeline specification" in log
    assert "bad exit code: 1" in log
    assert log.endswith("Completed with errors.\n")


def test_help():
    with raises(SystemExit) as exception_info:
        main(["--help"])
    assert 0 in exception_info.value.args


def test_invalid_input(tmp_path):
    cli_args = ["no_such_file", '--out-dir', tmp_path.as_posix(), '--out-id', "test"]
    with raises(FileNotFoundError) as exception_info:
        main(cli_args)
    assert 2 in exception_info.value.args

    with open(Path(tmp_path, "no_such_file", "test", "proceed.log")) as f:
        log = f.read()

    assert log.endswith("Parsing proceed pipeline specification from: no_such_file\n")

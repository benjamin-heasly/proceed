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
            StepResult(
                name="hello",
                exit_code=0,
                image_id=alpine_image.id,
                log_file=Path(tmp_path, "happy_spec", "test", "hello.log").as_posix()
            )
        ]
    )

    with open(Path(tmp_path, "happy_spec", "test", "execution_record.yaml")) as f:
        pipeline_result = PipelineResult.from_yaml(f.read())

    assert pipeline_result == expected_result

    with open(pipeline_result.step_results[0].log_file) as f:
        step_log = f.read()
    assert step_log == "quux\n"

    with open(Path(tmp_path, "happy_spec", "test", "proceed.log")) as f:
        log = f.read()

    # The cli log should contain messages from the proceed runner itself.
    # It should also contain the step logs.
    assert "Parsing proceed pipeline specification" in log
    assert "quux\n" in log
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
            StepResult(
                name="bad",
                exit_code=1,
                image_id=alpine_image.id,
                log_file=Path(tmp_path, "sad_spec", "test", "bad.log").as_posix()
            )
        ]
    )

    with open(Path(tmp_path, "sad_spec", "test", "execution_record.yaml")) as f:
        pipeline_result = PipelineResult.from_yaml(f.read())

    assert pipeline_result == expected_result

    with open(pipeline_result.step_results[0].log_file) as f:
        step_log = f.read()
    assert step_log == "ls: no_such_dir: No such file or directory\n"

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


def test_default_output_dirs(fixture_files, tmp_path):
    pipeline_spec = fixture_files['happy_spec.yaml'].as_posix()
    cli_args = [pipeline_spec, '--out-dir', tmp_path.as_posix()]
    exit_code = main(cli_args)
    assert exit_code == 0

    # We know the "group dir" that contains outputs for this pipeline spec is based on the spec file name.
    # We don't know the "id dir" that contains outputs for this specific execution, that's based on a timestamp.
    # But we know what to expect inside it, so we just search by matching.
    group_dir = Path(tmp_path, "happy_spec")

    # We should get an execution record.
    yaml_out = list(group_dir.glob("**/*.yaml"))
    assert len(yaml_out) == 1
    assert yaml_out[0].name == "execution_record.yaml"

    with open(yaml_out[0]) as f:
        pipeline_result = PipelineResult.from_yaml(f.read())

    # From the execution record we can discover the step log file(s).
    assert len(pipeline_result.step_results) == 1
    with open(pipeline_result.step_results[0].log_file) as f:
         step_log = f.read()
    assert step_log == "foo\n"

    # We should also get a log for the overall execution.
    proceed_log_out = list(group_dir.glob("**/proceed.log"))
    assert len(proceed_log_out) == 1
    assert proceed_log_out[0].name == "proceed.log"

    with open(proceed_log_out[0]) as f:
         proceed_log = f.read()

    assert "Parsing proceed pipeline specification" in proceed_log
    assert "foo\n" in proceed_log
    assert proceed_log.endswith("OK.\n")

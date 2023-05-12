import docker
import yaml
from pathlib import Path
from pytest import fixture, raises
from pandas import read_csv
from proceed.cli import main
from proceed.model import Pipeline, ExecutionRecord, StepResult


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
def fixture_specs(fixture_path):
    yaml_files = fixture_path.glob("*.yaml")
    return {yaml_file.name: yaml_file for yaml_file in yaml_files}


def test_happy_pipeline(fixture_specs, tmp_path, alpine_image):
    pipeline_spec = fixture_specs['happy_spec.yaml'].as_posix()
    cli_args = ["run", pipeline_spec,
                '--results-dir', tmp_path.as_posix(),
                '--results-id', "test",
                '--args', 'arg_1=quux']
    exit_code = main(cli_args)
    assert exit_code == 0

    with open(pipeline_spec) as f:
        original = Pipeline.from_yaml(f.read())

    expected_result = ExecutionRecord(
        original=original,
        amended=original._with_args_applied({"arg_1": "quux"}),
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
        pipeline_result = ExecutionRecord.from_yaml(f.read())

    assert pipeline_result == expected_result

    with open(pipeline_result.step_results[0].log_file) as f:
        step_log = f.read()
    assert step_log == "quux\n"

    with open(Path(tmp_path, "happy_spec", "test", "proceed.log")) as f:
        log = f.read()

    # The cli log should contain messages from the proceed runner itself.
    # It should also contain the step logs.
    assert "Parsing pipeline specification" in log
    assert "quux\n" in log
    assert log.endswith("OK.\n")

    # The cli should write out the effective config that was used
    with open(Path(tmp_path, "happy_spec", "test", "effective_options.yaml")) as f:
        effective_config_options = yaml.safe_load(f.read())
    assert effective_config_options["results_dir"] == tmp_path.as_posix()
    assert effective_config_options["args"] == {"arg_1": "quux"}


def test_sad_pipeline(fixture_specs, tmp_path, alpine_image):
    pipeline_spec = fixture_specs['sad_spec.yaml'].as_posix()
    cli_args = ["run", pipeline_spec, '--results-dir', tmp_path.as_posix(), '--results-id', "test",
                '--args', 'arg_1=quux']
    exit_code = main(cli_args)
    assert exit_code == 1

    with open(pipeline_spec) as f:
        original = Pipeline.from_yaml(f.read())

    expected_result = ExecutionRecord(
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
        pipeline_result = ExecutionRecord.from_yaml(f.read())

    assert pipeline_result == expected_result

    with open(pipeline_result.step_results[0].log_file) as f:
        step_log = f.read()
    assert step_log == "ls: no_such_dir: No such file or directory\n"

    with open(Path(tmp_path, "sad_spec", "test", "proceed.log")) as f:
        log = f.read()

    assert "Parsing pipeline specification" in log
    assert "bad exit code: 1" in log
    assert log.endswith("Completed with errors.\n")


def test_help():
    with raises(SystemExit) as exception_info:
        main(["--help"])
    assert 0 in exception_info.value.args


def test_invalid_input(tmp_path):
    cli_args = ["run", "no_such_file", '--results-dir', tmp_path.as_posix(), '--results-id', "test"]
    with raises(FileNotFoundError) as exception_info:
        main(cli_args)
    assert 2 in exception_info.value.args

    with open(Path(tmp_path, "no_such_file", "test", "proceed.log")) as f:
        log = f.read()

    assert log.endswith("Parsing pipeline specification from: no_such_file\n")


def test_spec_required_for_run():
    cli_args = ["run"]
    exit_code = main(cli_args)
    assert exit_code == -1


def test_default_output_dirs(fixture_specs, tmp_path):
    pipeline_spec = fixture_specs['happy_spec.yaml'].as_posix()
    cli_args = ["run", pipeline_spec, '--results-dir', tmp_path.as_posix()]
    exit_code = main(cli_args)
    assert exit_code == 0

    # We know the "group dir" that contains outputs for this pipeline spec is based on the spec file name.
    # We don't know the "id dir" that contains outputs for this specific execution, that's based on a timestamp.
    # But we know what to expect inside it, so we just search by matching.
    group_dir = Path(tmp_path, "happy_spec")

    # We should get an execution record.
    yaml_out = list(group_dir.glob("**/execution_record.yaml"))
    assert len(yaml_out) == 1
    assert yaml_out[0].name == "execution_record.yaml"

    with open(yaml_out[0]) as f:
        pipeline_result = ExecutionRecord.from_yaml(f.read())

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

    assert "Parsing pipeline specification" in proceed_log
    assert "foo\n" in proceed_log
    assert proceed_log.endswith("OK.\n")


def test_summarize_results(fixture_specs, tmp_path):
    # Run a pipeline that generates files, give us some results to summarize.
    pipeline_spec = fixture_specs['files_spec.yaml'].as_posix()
    work_dir = Path(tmp_path, "work").as_posix()
    run_args = ["run", pipeline_spec, '--results-dir', tmp_path.as_posix(), '--args', f"work_dir={work_dir}"]
    run_exit_code = main(run_args)
    assert run_exit_code == 0

    # Summarize the results from that pipeline.
    out_path = Path(tmp_path, "summary.csv")
    summarize_args = [
        "summarize",
        "--results-dir",
        tmp_path.as_posix(),
        "--summary-file",
        out_path.as_posix(),
        "--summary-sort-rows-by",
        "step_start",
        "file_role",
        "--summary-columns",
        "step_start",
        "results_group",
        "file_role",
        "file_path",
        "file_digest"]
    summarize_exit_code = main(summarize_args)
    assert summarize_exit_code == 0

    # The summary should have a file per row, check the summary at that level.
    summary = read_csv(out_path)
    assert summary["results_group"].to_list() == [
        "files_spec",
        "files_spec",
        "files_spec",
        "files_spec",
        "files_spec",
        "files_spec"]
    assert summary["file_role"].to_list() == [
        "log",
        "out",
        "in",
        "log",
        "out",
        "summary"]
    assert summary["file_path"].to_list() == [
        "create_file.log",
        "file.txt",
        "file.txt",
        "write_to_file.log",
        "file.txt",
        "file.txt"]
    assert summary["file_digest"].to_list() == [
        "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "sha256:12a61f4e173fb3a11c05d6471f74728f76231b4a5fcd9667cef3af87a3ae4dc2",
        "sha256:12a61f4e173fb3a11c05d6471f74728f76231b4a5fcd9667cef3af87a3ae4dc2",
    ]


def test_force_rerun(fixture_specs, tmp_path):
    # Run a pipeline that creates a and skips that step if already created.
    pipeline_spec = fixture_specs['files_spec.yaml'].as_posix()
    work_dir = Path(tmp_path, "work").as_posix()
    first_args = ["run", pipeline_spec,
                  '--results-dir', tmp_path.as_posix(),
                  '--args', f"work_dir={work_dir}",
                  '--results-id', "test_1"]
    first_exit_code = main(first_args)
    assert first_exit_code == 0

    second_args = ["run", pipeline_spec,
                   '--results-dir', tmp_path.as_posix(),
                   '--args', f"work_dir={work_dir}",
                   '--results-id', "test_2",
                   '--force-rerun']
    second_exit_code = main(second_args)
    assert second_exit_code == 0

    with open(Path(tmp_path, "files_spec", "test_2", "execution_record.yaml")) as f:
        rerun_result = ExecutionRecord.from_yaml(f.read())

    # The step should have done files present *and* results of re-execution
    rerun_create_file = rerun_result.step_results[0]
    assert rerun_create_file.name == "create file"
    assert work_dir in rerun_create_file.files_done
    assert "file.txt" in rerun_create_file.files_done[work_dir]
    assert rerun_create_file.exit_code == 0
    assert rerun_create_file.skipped == False


def test_steps_to_run(fixture_specs, tmp_path):
    pipeline_spec = fixture_specs['happy_spec.yaml'].as_posix()

    run_hello_args = ["run", pipeline_spec,
                      '--results-dir', tmp_path.as_posix(),
                      '--results-id', 'test_1',
                      '--step-names', 'hello']
    run_hello_exit_code = main(run_hello_args)
    assert run_hello_exit_code == 0
    with open(Path(tmp_path, "happy_spec", "test_1", "execution_record.yaml")) as f:
        run_hello_result = ExecutionRecord.from_yaml(f.read())
    assert len(run_hello_result.step_results) == 1
    assert run_hello_result.step_results[0].name == "hello"

    skip_hello_args = ["run", pipeline_spec,
                       '--results-dir', tmp_path.as_posix(),
                       '--results-id', 'test_2',
                       '--step-names', 'garbage']
    skip_hello_exit_code = main(skip_hello_args)
    assert skip_hello_exit_code == 0
    with open(Path(tmp_path, "happy_spec", "test_2", "execution_record.yaml")) as f:
        skip_hello_result = ExecutionRecord.from_yaml(f.read())
    assert len(skip_hello_result.step_results) == 0


def test_custom_options_file(fixture_path, fixture_specs, tmp_path):
    pipeline_spec = fixture_specs['happy_spec.yaml'].as_posix()
    custom_options = Path(fixture_path, 'config_options', 'custom_options.yaml').as_posix()
    run_args = ["run", pipeline_spec,
                '--results-dir', tmp_path.as_posix(),
                '--results-id', 'test',
                '--custom-options-file', custom_options]
    exit_code = main(run_args)
    assert exit_code == 0

    # The cli should pick up the custom options specified with --custom-options-file.
    with open(Path(tmp_path, "happy_spec", "test", "effective_options.yaml")) as f:
        effective_config_options = yaml.safe_load(f.read())
    assert effective_config_options["results_dir"] == tmp_path.as_posix()
    assert effective_config_options["args"] == {"extra_dir": "/custom/data/dir"}


def test_user_options_file(fixture_path, fixture_specs, tmp_path):
    pipeline_spec = fixture_specs['happy_spec.yaml'].as_posix()
    user_options = Path(fixture_path, 'config_options', 'user_options.yaml').as_posix()
    run_args = ["run", pipeline_spec,
                '--results-dir', tmp_path.as_posix(),
                '--results-id', 'test',
                '--user-options-file', user_options]
    exit_code = main(run_args)
    assert exit_code == 0

    # The cli should pick up the custom options specified with --user-options-file.
    with open(Path(tmp_path, "happy_spec", "test", "effective_options.yaml")) as f:
        effective_config_options = yaml.safe_load(f.read())
    assert effective_config_options["results_dir"] == tmp_path.as_posix()
    assert effective_config_options["args"] == {"data_dir": "/user/data/dir"}


def test_local_options_file(fixture_path, fixture_specs, tmp_path):
    pipeline_spec = fixture_specs['happy_spec.yaml'].as_posix()
    local_options = Path(fixture_path, 'config_options', 'local_options.yaml').as_posix()
    run_args = ["run", pipeline_spec,
                '--results-dir', tmp_path.as_posix(),
                '--results-id', 'test',
                '--local-options-file', local_options]
    exit_code = main(run_args)
    assert exit_code == 0

    # The cli should pick up the custom options specified with --local-options-file.
    with open(Path(tmp_path, "happy_spec", "test", "effective_options.yaml")) as f:
        effective_config_options = yaml.safe_load(f.read())
    assert effective_config_options["results_dir"] == tmp_path.as_posix()
    assert effective_config_options["args"] == {"data_dir": "/local/data/dir"}

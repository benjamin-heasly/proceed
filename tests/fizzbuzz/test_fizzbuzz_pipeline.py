from pathlib import Path
from os import getcwd
import docker
from pytest import fixture
from proceed.model import ExecutionRecord, StepResult
from proceed.cli import main
from proceed.file_matching import hash_contents


@fixture
def fizzbuzz_image(request):
    """The python:3.7 image must be present on the host, and/or we must be on the network."""
    this_file = Path(request.module.__file__)
    fizzbuzz_path = Path(this_file.parent.parent.parent, "src", "fizzbuzz")

    client = docker.from_env()
    (image, _) = client.images.build(path=str(fizzbuzz_path), tag="fizzbuzz:test")
    return image


@fixture
def fixture_path(request):
    this_file = Path(request.module.__file__).relative_to(getcwd())
    return Path(this_file.parent, 'fixture_files')


@fixture
def fixture_files(fixture_path):
    text_files = list(fixture_path.glob("*.txt"))
    yaml_files = list(fixture_path.glob("*.yaml"))
    return {text_file.name: text_file for text_file in text_files + yaml_files}


@fixture
def fixture_digests(fixture_files):
    return {file_name: hash_contents(file) for file_name, file in fixture_files.items()}


def test_pipeline(fizzbuzz_image, fixture_path, tmp_path, fixture_files, fixture_digests):
    # First run through the pipeline should succeed and see expected input and output files.
    pipeline_spec = fixture_files["fizzbuzz_pipeline_spec.yaml"].as_posix()
    args = [
        "run",
        pipeline_spec,
        '--results-dir', tmp_path.as_posix(),
        '--results-group', "fizzbuzz",
        '--results-id', "test",
        '--args', f"data_dir={fixture_path.as_posix()}", f"work_dir={tmp_path.as_posix()}"
    ]

    exit_code = main(args)
    assert exit_code == 0

    with open(Path(tmp_path, "fizzbuzz", "test", "execution_record.yaml"), 'r') as f:
        results_yaml = f.read()
        pipeline_results = ExecutionRecord.from_yaml(results_yaml)

    assert pipeline_results.timing._is_complete()
    assert len(pipeline_results.step_results) == 3

    classify_result = pipeline_results.step_results[0]
    classify_expected = StepResult(
        name="classify",
        image_id=fizzbuzz_image.id,
        exit_code=0,
        log_file=Path(tmp_path, "fizzbuzz", "test", "classify.log").as_posix(),
        files_done={},
        files_in={
            fixture_path.as_posix(): {'classify_in.txt': fixture_digests["classify_in.txt"]}
        },
        files_out={
            tmp_path.as_posix(): {'classify_out.txt': fixture_digests["classify_expected.txt"]}
        }
    )
    assert classify_result == classify_expected
    assert classify_result.timing._is_complete()
    with open(classify_result.log_file, 'r') as f:
        classify_logs = f.read()
    assert classify_logs == "OK.\n"

    filter_fizz_result = pipeline_results.step_results[1]
    filter_fizz_expected = StepResult(
        name="filter fizz",
        image_id=fizzbuzz_image.id,
        exit_code=0,
        log_file=Path(tmp_path, "fizzbuzz", "test", "filter_fizz.log").as_posix(),
        files_done={},
        files_in={
            tmp_path.as_posix(): {'classify_out.txt': fixture_digests["classify_expected.txt"]}
        },
        files_out={
            tmp_path.as_posix(): {'filter_fizz_out.txt': fixture_digests["filter_fizz_expected.txt"]}
        }
    )
    assert filter_fizz_result == filter_fizz_expected
    assert filter_fizz_result.timing._is_complete()
    with open(filter_fizz_result.log_file, 'r') as f:
        filter_fizz_logs = f.read()
    assert filter_fizz_logs == "OK.\n"

    filter_buzz_result = pipeline_results.step_results[2]
    filter_buzz_expected = StepResult(
        name="filter buzz",
        image_id=fizzbuzz_image.id,
        exit_code=0,
        log_file=Path(tmp_path, "fizzbuzz", "test", "filter_buzz.log").as_posix(),
        files_done={},
        files_in={
            tmp_path.as_posix(): {'filter_fizz_out.txt': fixture_digests["filter_fizz_expected.txt"]}
        },
        files_out={
            tmp_path.as_posix(): {'filter_buzz_out.txt': fixture_digests["filter_buzz_expected.txt"]}
        }
    )
    assert filter_buzz_result == filter_buzz_expected
    assert filter_buzz_result.timing._is_complete()
    with open(filter_buzz_result.log_file, 'r') as f:
        filter_buzz_logs = f.read()
    assert filter_buzz_logs == "OK.\n"

    with open(Path(tmp_path, "fizzbuzz", "test", "proceed.log")) as f:
        log = f.read()

    assert "Parsing pipeline specification" in log
    assert log.endswith("OK.\n")


def test_pipeline_skip_done_steps(fizzbuzz_image, fixture_path, tmp_path, fixture_files, fixture_digests):
    # Repeat run through the pipeline should succeed and skip steps because they already have "done" files.
    pipeline_spec = fixture_files["fizzbuzz_pipeline_spec.yaml"].as_posix()
    args = [
        "run",
        pipeline_spec,
        '--results-dir', tmp_path.as_posix(),
        '--results-group', "fizzbuzz",
        '--results-id', "test",
        '--args', f"data_dir={fixture_path.as_posix()}", f"work_dir={tmp_path.as_posix()}"
    ]

    # Run the pipeline twice.
    exit_code = main(args)
    assert exit_code == 0

    repeat_exit_code = main(args)
    assert repeat_exit_code == 0

    with open(Path(tmp_path, "fizzbuzz", "test", "execution_record.yaml"), 'r') as f:
        results_yaml = f.read()
        pipeline_results = ExecutionRecord.from_yaml(results_yaml)

    assert pipeline_results.timing._is_complete()
    assert len(pipeline_results.step_results) == 3

    classify_result = pipeline_results.step_results[0]
    classify_expected = StepResult(
        name="classify",
        skipped=True,
        files_done={
            tmp_path.as_posix(): {'classify_out.txt': fixture_digests["classify_expected.txt"]}
        }
    )
    assert classify_result == classify_expected

    filter_fizz_result = pipeline_results.step_results[1]
    filter_fizz_expected = StepResult(
        name="filter fizz",
        skipped=True,
        files_done={
            tmp_path.as_posix(): {'filter_fizz_out.txt': fixture_digests["filter_fizz_expected.txt"]}
        }
    )
    assert filter_fizz_result == filter_fizz_expected

    filter_buzz_result = pipeline_results.step_results[2]
    filter_buzz_expected = StepResult(
        name="filter buzz",
        skipped=True,
        files_done={
            tmp_path.as_posix(): {'filter_buzz_out.txt': fixture_digests["filter_buzz_expected.txt"]}
        }
    )
    assert filter_buzz_result == filter_buzz_expected

    with open(Path(tmp_path, "fizzbuzz", "test", "proceed.log")) as f:
        log = f.read()

    assert "Parsing pipeline specification" in log
    assert log.endswith("OK.\n")

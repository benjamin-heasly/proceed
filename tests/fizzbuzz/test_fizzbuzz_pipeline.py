from pathlib import Path
from os import getcwd
import docker
from pytest import fixture
from proceed.model import PipelineResult, StepResult
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


def test_pipeline(fizzbuzz_image, fixture_path, tmp_path, fixture_files):
    # First run through the pipeline should succeed and see expected input and output files.
    pipeline_spec = fixture_files["fizzbuzz_pipeline_spec.yaml"].as_posix()
    record = Path(tmp_path, 'fizzbuzz_record.yaml').as_posix()
    args = [
        pipeline_spec,
        '--record', record,
        '--args', f"data_dir={fixture_path.as_posix()}", f"work_dir={tmp_path.as_posix()}"
    ]

    exit_code = main(args)
    assert exit_code == 0

    with open(record, 'r') as f:
        results_yaml = f.read()
        pipeline_results = PipelineResult.from_yaml(results_yaml)

    assert pipeline_results.timing.is_complete()
    assert len(pipeline_results.step_results) == 3

    classify_result = pipeline_results.step_results[0]
    classify_expected = StepResult(
        name="classify",
        image_id=fizzbuzz_image.id,
        exit_code=0,
        logs="OK.\n",
        files_done={},
        files_in={
            fixture_path.as_posix(): {'classify_in.txt': hash_contents(fixture_files["classify_in.txt"])}
        },
        files_out={
            tmp_path.as_posix(): {'classify_out.txt': hash_contents(fixture_files["classify_expected.txt"])}
        }
    )
    assert classify_result == classify_expected
    assert classify_result.timing.is_complete()

    filter_fizz_result = pipeline_results.step_results[1]
    filter_fizz_expected = StepResult(
        name="filter fizz",
        image_id=fizzbuzz_image.id,
        exit_code=0,
        logs="OK.\n",
        files_done={},
        files_in={
            tmp_path.as_posix(): {'classify_out.txt': hash_contents(fixture_files["classify_expected.txt"])}
        },
        files_out={
            tmp_path.as_posix(): {'filter_fizz_out.txt': hash_contents(fixture_files["filter_fizz_expected.txt"])}
        }
    )
    assert filter_fizz_result == filter_fizz_expected
    assert filter_fizz_result.timing.is_complete()

    filter_buzz_result = pipeline_results.step_results[2]
    filter_buzz_expected = StepResult(
        name="filter buzz",
        image_id=fizzbuzz_image.id,
        exit_code=0,
        logs="OK.\n",
        files_done={},
        files_in={
            tmp_path.as_posix(): {'filter_fizz_out.txt': hash_contents(fixture_files["filter_fizz_expected.txt"])}
        },
        files_out={
            tmp_path.as_posix(): {'filter_buzz_out.txt': hash_contents(fixture_files["filter_buzz_expected.txt"])}
        }
    )
    assert filter_buzz_result == filter_buzz_expected
    assert filter_buzz_result.timing.is_complete()


def test_pipeline_skip_done_steps(fizzbuzz_image, fixture_path, tmp_path, fixture_files):
    # Repeat run through the pipeline should succeed and skip steps because they already have "done" files.
    pipeline_spec = fixture_files["fizzbuzz_pipeline_spec.yaml"].as_posix()
    record = Path(tmp_path, 'fizzbuzz_record.yaml').as_posix()
    args = [
        pipeline_spec,
        '--record', record,
        '--args', f"data_dir={fixture_path.as_posix()}", f"work_dir={tmp_path.as_posix()}"
    ]

    # Run the pipeline twice.
    exit_code = main(args)
    assert exit_code == 0

    repeat_exit_code = main(args)
    assert repeat_exit_code == 0

    with open(record, 'r') as f:
        results_yaml = f.read()
        pipeline_results = PipelineResult.from_yaml(results_yaml)

    assert pipeline_results.timing.is_complete()
    assert len(pipeline_results.step_results) == 3

    classify_result = pipeline_results.step_results[0]
    classify_expected = StepResult(
        name="classify",
        skipped=True,
        files_done={
            tmp_path.as_posix(): {'classify_out.txt': hash_contents(fixture_files["classify_expected.txt"])}
        }
    )
    assert classify_result == classify_expected

    filter_fizz_result = pipeline_results.step_results[1]
    filter_fizz_expected = StepResult(
        name="filter fizz",
        skipped=True,
        files_done={
            tmp_path.as_posix(): {'filter_fizz_out.txt': hash_contents(fixture_files["filter_fizz_expected.txt"])}
        }
    )
    assert filter_fizz_result == filter_fizz_expected

    filter_buzz_result = pipeline_results.step_results[2]
    filter_buzz_expected = StepResult(
        name="filter buzz",
        skipped=True,
        files_done={
            tmp_path.as_posix(): {'filter_buzz_out.txt': hash_contents(fixture_files["filter_buzz_expected.txt"])}
        }
    )
    assert filter_buzz_result == filter_buzz_expected

from pathlib import Path
from os import getcwd
import docker
from pytest import fixture
from proceed.model import PipelineResult, StepResult
from proceed.cli import main


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


def assert_files_equal(a_file, b_file):
    with open(a_file) as a:
        a_text = a.read()
    with open(b_file) as b:
        b_text = b.read()
    assert a_text == b_text


def test_pipeline(fizzbuzz_image, fixture_path, tmp_path, fixture_files):
    pipeline_spec = fixture_files["fizzbuzz_pipeline.yaml"].as_posix()
    record = Path(tmp_path, 'fizzbuzz_record.yaml').as_posix()
    args = [pipeline_spec, '--record', record, '--args', f"data_dir={fixture_path.as_posix()}", f"work_dir={tmp_path.as_posix()}"]
    exit_code = main(args)
    assert exit_code == 0

    with open(record, 'r') as f:
        results_yaml = f.read()
        pipeline_results = PipelineResult.from_yaml(results_yaml)
    print(results_yaml)
    expected_step_results = [
        StepResult(name="classify", image_id=fizzbuzz_image.id, exit_code=0, logs="OK.\n"),
        StepResult(name="filter fizz", image_id=fizzbuzz_image.id, exit_code=0, logs="OK.\n"),
        StepResult(name="filter buzz", image_id=fizzbuzz_image.id, exit_code=0, logs="OK.\n")
    ]
    assert pipeline_results.step_results == expected_step_results

    # All steps should have expected side-effects of files processed.
    assert_files_equal(Path(tmp_path, "classify_out.txt"), fixture_files['classify_expected.txt'])
    assert_files_equal(Path(tmp_path, "filter_fizz_out.txt"), fixture_files['filter_fizz_expected.txt'])
    assert_files_equal(Path(tmp_path, "filter_buzz_out.txt"), fixture_files['filter_buzz_expected.txt'])

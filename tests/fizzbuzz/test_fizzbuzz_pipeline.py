from pathlib import Path
import docker
from pytest import fixture, raises
from pipeline_stuff.model import Pipeline, Step
from pipeline_stuff.docker_runner import run_pipeline, run_step


@fixture
def fizzbuzz_path(request):
    this_file = Path(request.module.__file__)
    return Path(this_file.parent.parent.parent, "src", "fizzbuzz")


@fixture
def fizzbuzz_image(fizzbuzz_path):
    client = docker.from_env()
    (image, _) = client.images.build(path=str(fizzbuzz_path), tag="fizzbuzz:test")
    return image


def test_help(fizzbuzz_image):
    step = Step(
        name="help",
        image=fizzbuzz_image.id,
        command=["--help"]
    )
    step_result = run_step(step)
    assert step_result.exit_code == 0
    assert step_result.logs.startswith("usage:")
    assert "show this help message and exit" in step_result.logs


def test_invalid_input(fizzbuzz_image):
    step = Step(
        name="invalid",
        image=fizzbuzz_image.id,
        command=["invalid"]
    )
    step_result = run_step(step)
    assert step_result.exit_code == 2
    assert step_result.logs.startswith("usage:")
    assert "the following arguments are required" in step_result.logs


@fixture
def fixture_path(request):
    this_file = Path(request.module.__file__)
    return Path(this_file.parent, 'fixture_files')


@fixture
def fixture_files(fixture_path):
    text_files = fixture_path.glob("*.txt")
    return {text_file.name: text_file for text_file in text_files}


def assert_files_equal(a_file, b_file):
    with open(a_file) as a:
        a_text = a.read()
    with open(b_file) as b:
        b_text = b.read()
    assert a_text == b_text


def test_pipeline(fizzbuzz_image, fixture_path, tmp_path, fixture_files):
    # Locate temp and fixture files to make available inside containers.
    volumes = {
        tmp_path.as_posix(): {"bind": "/tmp/fizzbuzz", "mode": "rw"},
        fixture_path.as_posix(): {"bind": "/var/fizzbuzz", "mode": "ro"},
    }

    # Create a "fizzbuzz" pipeline of three steps.
    classify_step = Step(
        name="classify",
        image=fizzbuzz_image.tags[0],
        volumes=volumes,
        command=["/var/fizzbuzz/classify_in.txt", "/tmp/fizzbuzz/classify_out.txt", "classify"]
    )
    filter_fizz_step = Step(
        name="filter fizz",
        image=fizzbuzz_image.tags[0],
        volumes=volumes,
        command=["/tmp/fizzbuzz/classify_out.txt", "/tmp/fizzbuzz/filter_fizz_out.txt", "filter", "--substring", "fizz"]
    )
    filter_buzz_step = Step(
        name="filter buzz",
        image=fizzbuzz_image.tags[0],
        volumes=volumes,
        command=["/tmp/fizzbuzz/filter_fizz_out.txt", "/tmp/fizzbuzz/filter_buzz_out.txt", "filter", "--substring", "buzz"]
    )

    # All steps should return with with happy status and clean logs.
    pipeline = Pipeline(steps=[classify_step, filter_fizz_step, filter_buzz_step])
    pipeline_results = run_pipeline(pipeline)
    assert all(result.exit_code == 0 for result in pipeline_results.step_results)
    assert all(result.logs.endswith("OK.\n") for result in pipeline_results.step_results)

    # Step results should be named like their original steps.
    result_names = [result.name for result in pipeline_results.step_results]
    expected_names = [step.name for step in pipeline.steps]
    assert result_names == expected_names

    # Step results should use the exact image id, as opposed to any of its tag.
    assert all(result.image_id == fizzbuzz_image.id for result in pipeline_results.step_results)

    # All steps should have expected side-effects on files processed.
    assert_files_equal(Path(tmp_path, "classify_out.txt"), fixture_files['classify_expected.txt'])
    assert_files_equal(Path(tmp_path, "filter_fizz_out.txt"), fixture_files['filter_fizz_expected.txt'])
    assert_files_equal(Path(tmp_path, "filter_buzz_out.txt"), fixture_files['filter_buzz_expected.txt'])

from pathlib import Path
import docker
from pytest import fixture
from proceed.model import Pipeline, Step, StepResult
from proceed.docker_runner import run_pipeline, run_step


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
    # Pipeline to run three containers from the fizzbuzz:test image created above.
    pipeline_spec = """
    version: 0.0.1
    args:
        data_dir: ""
        work_dir: ""
    volumes:
        "$data_dir": {"bind": /data, "mode": "ro"}
        "$work_dir": /work
    steps:
        - name: classify
          image: fizzbuzz:test
          command: ["/data/classify_in.txt", "/work/classify_out.txt", "classify"]
        - name: filter fizz
          image: fizzbuzz:test
          command: ["/work/classify_out.txt", "/work/filter_fizz_out.txt", "filter", "--substring", "fizz"]
        - name: filter buzz
          image: fizzbuzz:test
          command: ["/work/filter_fizz_out.txt", "/work/filter_buzz_out.txt", "filter", "--substring", "buzz"]
        """
    pipeline = Pipeline.from_yaml(pipeline_spec)

    # Dynamically bind the data and temp dirs that we don't know until runtime.
    args = {
        "data_dir": fixture_path.as_posix(),
        "work_dir": tmp_path.as_posix()
    }

    # Each step should report clean exit status and logs.
    # Step results should use the image's explicit content hash / id, rather than a given alias or tag.
    pipeline_results = run_pipeline(pipeline, args)
    expected_step_results = [
        StepResult(name="classify", image_id=fizzbuzz_image.id, exit_code=0, logs="OK.\n"),
        StepResult(name="filter fizz", image_id=fizzbuzz_image.id, exit_code=0, logs="OK.\n"),
        StepResult(name="filter buzz", image_id=fizzbuzz_image.id, exit_code=0, logs="OK.\n")
    ]
    assert pipeline_results.results == expected_step_results

    # All steps should have expected side-effects of files processed.
    assert_files_equal(Path(tmp_path, "classify_out.txt"), fixture_files['classify_expected.txt'])
    assert_files_equal(Path(tmp_path, "filter_fizz_out.txt"), fixture_files['filter_fizz_expected.txt'])
    assert_files_equal(Path(tmp_path, "filter_buzz_out.txt"), fixture_files['filter_buzz_expected.txt'])

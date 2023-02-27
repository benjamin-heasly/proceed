from pathlib import Path
from pytest import fixture, raises

import docker


@fixture
def fizzbuzz_path(request):
    this_file = Path(request.module.__file__)
    return Path(this_file.parent.parent.parent, "src", "fizzbuzz")


@fixture
def fizzbuzz_image(fizzbuzz_path):
    client = docker.from_env()
    (image, _) = client.images.build(path=str(fizzbuzz_path), tag="fizzbuzz:test")
    return image


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


def test_help(fizzbuzz_image):
    client = docker.from_env()
    log_bytes = client.containers.run(fizzbuzz_image.id, command="--help")
    log_str = log_bytes.decode("utf-8")
    assert log_str.startswith("usage:")
    assert "show this help message and exit" in log_str


def test_invalid_input(fizzbuzz_image):
    client = docker.from_env()
    with raises(docker.errors.ContainerError) as exception_info:
        client.containers.run(fizzbuzz_image.id, command="invalid")
    assert exception_info.value.exit_status == 2
    log_bytes = exception_info.value.container.logs()
    log_str = log_bytes.decode("utf-8")
    assert log_str.startswith("usage:")
    assert "the following arguments are required" in log_str


def run_fizzbuzz_container(fizzbuzz_image, fixture_path, tmp_path, command):
    # Mount local fixture and temp dirs inside a container, with the same path names.
    volumes = {
        tmp_path.as_posix(): {"bind": tmp_path.as_posix(), "mode": "rw"},
        fixture_path.as_posix(): {"bind": fixture_path.as_posix(), "mode": "ro"},
    }
    client = docker.from_env()
    log_bytes = client.containers.run(
        fizzbuzz_image.id, volumes=volumes, command=command)
    return log_bytes.decode("utf-8")


def test_classify_lines(fizzbuzz_image, fixture_path, fixture_files, tmp_path):
    out_file = Path(tmp_path, 'classify_out.txt')
    command = [fixture_files['classify_in.txt'].as_posix(),
               out_file.as_posix(), "classify"]
    log_str = run_fizzbuzz_container(
        fizzbuzz_image, fixture_path, tmp_path, command)
    assert log_str.endswith("OK.\n")
    assert_files_equal(out_file, fixture_files['classify_expected.txt'])


def test_filter_fizz_lines(fizzbuzz_image, fixture_path, fixture_files, tmp_path):
    out_file = Path(tmp_path, 'filter_fizz_out.txt')
    command = [fixture_files['classify_expected.txt'].as_posix(
    ), out_file.as_posix(), "filter", "--substring", "fizz"]
    log_str = run_fizzbuzz_container(
        fizzbuzz_image, fixture_path, tmp_path, command)
    assert log_str.endswith("OK.\n")
    assert_files_equal(out_file, fixture_files['filter_fizz_expected.txt'])


def test_filter_buzz_lines(fizzbuzz_image, fixture_path, fixture_files, tmp_path):
    out_file = Path(tmp_path, 'filter_buzz_out.txt')
    command = [fixture_files['filter_fizz_expected.txt'].as_posix(
    ), out_file.as_posix(), "filter", "--substring", "buzz"]
    log_str = run_fizzbuzz_container(
        fizzbuzz_image, fixture_path, tmp_path, command)
    assert log_str.endswith("OK.\n")
    assert_files_equal(out_file, fixture_files['filter_buzz_expected.txt'])

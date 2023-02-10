from pathlib import Path
from pytest import fixture, raises

from pipeline_stuff.fizzbuzz import fizzbuzz_runner

@fixture
def test_files(request):
    test_dir = Path(request.module.__file__).parent
    files_dir = Path(test_dir, 'fixture_files')
    text_files = files_dir.glob("*.txt")
    return { text_file.name:text_file for text_file in text_files }

def assert_files_equal(a_file, b_file):
    with open(a_file) as a:
        a_text = a.read()

    with open(b_file) as b:
        b_text = b.read()

    assert a_text == b_text

def test_help():
    with raises(SystemExit) as exception_info:
        fizzbuzz_runner.main(["--help"])
    assert 0 in exception_info.value.args

def test_invalid_input():
    with raises(SystemExit) as exception_info:
        fizzbuzz_runner.main(["invalid"])
    assert 2 in exception_info.value.args

def test_classify_lines(test_files, tmp_path):
    out_file = Path(tmp_path, 'classify_out.txt')
    exit_code = fizzbuzz_runner.main([test_files['classify_in.txt'].as_posix(), out_file.as_posix(), "classify"])
    assert not exit_code
    assert_files_equal(out_file, test_files['classify_expected.txt'])

def test_filter_fizz_lines(test_files, tmp_path):
    out_file = Path(tmp_path, 'filter_fizz_out.txt')
    exit_code = fizzbuzz_runner.main([test_files['classify_expected.txt'].as_posix(), out_file.as_posix(), "filter", "--substring", "fizz"])
    assert not exit_code
    assert_files_equal(out_file, test_files['filter_fizz_expected.txt'])

def test_filter_buzz_lines(test_files, tmp_path):
    out_file = Path(tmp_path, 'filter_buzz_out.txt')
    exit_code = fizzbuzz_runner.main([test_files['filter_fizz_expected.txt'].as_posix(), out_file.as_posix(), "filter", "--substring", "buzz"])
    assert not exit_code
    assert_files_equal(out_file, test_files['filter_buzz_expected.txt'])

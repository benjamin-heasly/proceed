from pathlib import Path
from pytest import fixture

from fizzbuzz import fizzbuzz

divisible_by_3 = set(range(0, 100, 3))
divisible_by_5 = set(range(0, 100, 5))

def test_divisible_by_3_only():
    for number in divisible_by_3 - divisible_by_5:
        suffix = fizzbuzz.classify(number)
        assert suffix == "fizz"

def test_divisible_by_5_only():
    for number in divisible_by_5 - divisible_by_3:
        suffix = fizzbuzz.classify(number)
        assert suffix == "buzz"

def test_divisible_by_3_and_5():
    for number in divisible_by_3.intersection(divisible_by_5):
        suffix = fizzbuzz.classify(number)
        assert suffix == "fizzbuzz"

def test_divisible_by_neither_3_nor_5():
    divisible_by_neither = set(range(0, 100)) - divisible_by_3 - divisible_by_5
    for number in divisible_by_neither:
        suffix = fizzbuzz.classify(number)
        assert not suffix

def test_append():
    assert fizzbuzz.append("0") == "0 fizzbuzz"
    assert fizzbuzz.append("1") == "1"
    assert fizzbuzz.append("2") == "2"
    assert fizzbuzz.append("3") == "3 fizz"
    assert fizzbuzz.append("4") == "4"
    assert fizzbuzz.append("5") == "5 buzz"
    assert fizzbuzz.append("15") == "15 fizzbuzz"

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

def test_classify_lines(test_files, tmp_path):
    out_file = Path(tmp_path, 'classify_out.txt')
    fizzbuzz.classify_lines(test_files['classify_in.txt'], out_file)
    assert_files_equal(out_file, test_files['classify_expected.txt'])

def test_filter_fizz_lines(test_files, tmp_path):
    out_file = Path(tmp_path, 'filter_fizz_out.txt')
    fizzbuzz.filter_lines(test_files['classify_expected.txt'], out_file, 'fizz')
    assert_files_equal(out_file, test_files['filter_fizz_expected.txt'])

def test_filter_buzz_lines(test_files, tmp_path):
    out_file = Path(tmp_path, 'filter_buzz_out.txt')
    fizzbuzz.filter_lines(test_files['filter_fizz_expected.txt'], out_file, 'buzz')
    assert_files_equal(out_file, test_files['filter_buzz_expected.txt'])

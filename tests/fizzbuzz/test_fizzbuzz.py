from pathlib import Path
from pytest import fixture

from pipeline_stuff.fizzbuzz import fizzbuzz

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
def in_file(request):
    test_dir = Path(request.module.__file__).parent
    return Path(test_dir, 'test_100_in.txt')

@fixture
def expected_file(request):
    test_dir = Path(request.module.__file__).parent
    return Path(test_dir, 'test_100_expected.txt')

def test_convert_tile(in_file, expected_file, tmp_path):
    out_file = Path(tmp_path, 'test_100_out.txt')
    fizzbuzz.convert_file(in_file, out_file)
    with open(out_file) as f:
        out_text = f.read()
    
    with open(expected_file) as f:
        expected_text = f.read()
    
    assert out_text == expected_text

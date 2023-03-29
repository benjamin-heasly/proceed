from pathlib import Path
from pytest import fixture
from proceed.file_matching import count_matches, flatten_matches, match_patterns_in_dirs


@fixture
def fixture_path(request):
    this_file = Path(request.module.__file__)
    return Path(this_file.parent, 'fixture_files')


def test_match_yaml_files(fixture_path):
    fixture_dir = fixture_path.as_posix()
    matched_files = match_patterns_in_dirs([fixture_dir], ["*.yaml"])
    expected_files = {
        fixture_dir: {
            "files_spec.yaml": "sha256:116834f180c480a1b9e7880c1f1b608d6ebb0bc2e373f72ffe278f8d4cd45b69",
            "happy_spec.yaml": "sha256:23b5688d1593f8479a42dad99efa791db4bf795de9330a06664ac22837fc3ecc",
            "sad_spec.yaml": "sha256:cc428c52c6c015b4680559a540cf0af5c3e7878cd711109b7f0fe0336e40b000",
        }
    }
    assert matched_files == expected_files
    assert count_matches(matched_files) == 3


def test_match_nonexistent_files(fixture_path):
    fixture_dir = fixture_path.as_posix()
    matched_files = match_patterns_in_dirs([fixture_dir], ["*.nonexistent"])
    assert not matched_files
    assert count_matches(matched_files) == 0


def test_ignore_directories(fixture_path):
    fixture_dir = fixture_path.as_posix()
    matched_files = match_patterns_in_dirs([fixture_dir], ["**/*spec.yaml"])
    expected_files = {
        fixture_dir: {
            "files_spec.yaml": "sha256:116834f180c480a1b9e7880c1f1b608d6ebb0bc2e373f72ffe278f8d4cd45b69",
            "happy_spec.yaml": "sha256:23b5688d1593f8479a42dad99efa791db4bf795de9330a06664ac22837fc3ecc",
            "sad_spec.yaml": "sha256:cc428c52c6c015b4680559a540cf0af5c3e7878cd711109b7f0fe0336e40b000",
        }
    }
    assert matched_files == expected_files
    assert count_matches(matched_files) == 3


def test_flatten_empty():
    empty_matches = {}
    flattened = flatten_matches(empty_matches)
    assert not flattened


def test_flatten_matches():
    matches = {
        "volume_a": {
            "file_1.txt": "sha256:11111111",
            "file_2.txt": "sha256:22222222",
        },
        "volume_b": {
            "file_3.txt": "sha256:33333333",
            "file_4.txt": "sha256:44444444",
        }
    }
    flattened = flatten_matches(matches, foo="bar")
    expected_flattened = [
        {"file_volume": "volume_a", "file_path": "file_1.txt", "file_digest": "sha256:11111111", "foo": "bar"},
        {"file_volume": "volume_a", "file_path": "file_2.txt", "file_digest": "sha256:22222222", "foo": "bar"},
        {"file_volume": "volume_b", "file_path": "file_3.txt", "file_digest": "sha256:33333333", "foo": "bar"},
        {"file_volume": "volume_b", "file_path": "file_4.txt", "file_digest": "sha256:44444444", "foo": "bar"},
    ]
    assert flattened == expected_flattened

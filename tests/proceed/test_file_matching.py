from pathlib import Path
from pytest import fixture
from proceed.file_matching import count_matches, match_patterns_in_dirs


@fixture
def fixture_path(request):
    this_file = Path(request.module.__file__)
    return Path(this_file.parent, 'fixture_files')


def test_match_yaml_files(fixture_path):
    fixture_dir = fixture_path.as_posix()
    matched_files = match_patterns_in_dirs([fixture_dir], ["*.yaml"])
    expected_files = {
        fixture_dir: {
            "happy_spec.yaml": "sha256:23b5688d1593f8479a42dad99efa791db4bf795de9330a06664ac22837fc3ecc",
            "sad_spec.yaml": "sha256:cc428c52c6c015b4680559a540cf0af5c3e7878cd711109b7f0fe0336e40b000",
        }
    }
    assert matched_files == expected_files
    assert count_matches(matched_files) == 2


def test_match_nonexistent_files(fixture_path):
    fixture_dir = fixture_path.as_posix()
    matched_files = match_patterns_in_dirs([fixture_dir], ["*.nonexistent"])
    assert not matched_files
    assert count_matches(matched_files) == 0


def test_ignore_directories(fixture_path):
    fixture_dir = fixture_path.as_posix()
    matched_files = match_patterns_in_dirs([fixture_dir], ["**/*"])
    expected_files = {
        fixture_dir: {
            "happy_spec.yaml": "sha256:23b5688d1593f8479a42dad99efa791db4bf795de9330a06664ac22837fc3ecc",
            "sad_spec.yaml": "sha256:cc428c52c6c015b4680559a540cf0af5c3e7878cd711109b7f0fe0336e40b000",
        }
    }
    assert matched_files == expected_files
    assert count_matches(matched_files) == 2

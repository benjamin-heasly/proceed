from pathlib import Path
from pytest import fixture
from argparse import ArgumentParser
from proceed.config_options import (
    ConfigOptions,
    ConvertingKeyValuePairsAction,
    KeyValuePairsAction,
    parse_key_value_pairs,
    resolve_config_options
)


@fixture
def fixture_path(request):
    this_file = Path(request.module.__file__)
    return Path(this_file.parent, 'fixture_files')


def test_parse_key_value_pairs():
    values = ["foo=bar", "baz=1", "quux=False", "flim=null"]
    key_value_pairs = parse_key_value_pairs(values, convert_values=False)
    assert key_value_pairs == {"foo": "bar", "baz": "1", "quux": "False", "flim": "null"}

    converted_key_value_pairs = parse_key_value_pairs(values, convert_values=True)
    assert converted_key_value_pairs == {"foo": "bar", "baz": 1, "quux": False, "flim": None}


def test_key_value_pairs_action():
    parser = ArgumentParser()
    parser.add_argument("--kvp", nargs="+", action=KeyValuePairsAction)
    parsed = parser.parse_args(["--kvp", "foo=bar", "baz=1", "quux=False", "flim=null"])
    assert parsed.kvp == {"foo": "bar", "baz": "1", "quux": "False", "flim": "null"}


def test_convertng_key_value_pairs_action():
    parser = ArgumentParser()
    parser.add_argument("--kvp", nargs="+", action=ConvertingKeyValuePairsAction)
    parsed = parser.parse_args(["--kvp", "foo=bar", "baz=1", "quux=False", "flim=null"])
    assert parsed.kvp == {"foo": "bar", "baz": 1, "quux": False, "flim": None}


def test_resolve_default_options():
    resolved_options = resolve_config_options()
    expected_options = ConfigOptions()
    assert resolved_options == expected_options


def test_resolve_user_options(fixture_path):
    user_options_file = Path(fixture_path, "config_options", "user_options.yaml").as_posix()
    preferred_options = {
        "user_options_file": user_options_file
    }
    resolved_options = resolve_config_options(preferred_options)

    expected_options = ConfigOptions()
    expected_options.set_value("user_options_file", user_options_file)
    expected_options.set_value("results_dir", "/user/results/dir")
    expected_options.set_value("args", {"data_dir": "/user/data/dir"})
    expected_options.set_value("yaml_options", {'default_flow_style': None, 'sort_keys': False, 'width': 100})

    assert resolved_options == expected_options


def test_resolve_user_and_local_options(fixture_path):
    user_options_file = Path(fixture_path, "config_options", "user_options.yaml").as_posix()
    local_options_file = Path(fixture_path, "config_options", "local_options.yaml").as_posix()
    preferred_options = {
        "user_options_file": user_options_file,
        "local_options_file": local_options_file
    }
    resolved_options = resolve_config_options(preferred_options)

    expected_options = ConfigOptions()
    expected_options.set_value("user_options_file", user_options_file)
    expected_options.set_value("local_options_file", local_options_file)
    expected_options.set_value("results_dir", "/local/results/dir")
    expected_options.set_value("args", {"data_dir": "/local/data/dir"})
    expected_options.set_value("yaml_options", {'default_flow_style': True, 'sort_keys': False, 'width': 100})

    assert resolved_options == expected_options


def test_resolve_user_local_and_custom_options(fixture_path):
    user_options_file = Path(fixture_path, "config_options", "user_options.yaml").as_posix()
    local_options_file = Path(fixture_path, "config_options", "local_options.yaml").as_posix()
    custom_options_file = Path(fixture_path, "config_options", "custom_options.yaml").as_posix()
    preferred_options = {
        "user_options_file": user_options_file,
        "local_options_file": local_options_file,
        "custom_options_file": custom_options_file,
    }
    resolved_options = resolve_config_options(preferred_options)

    expected_options = ConfigOptions()
    expected_options.set_value("user_options_file", user_options_file)
    expected_options.set_value("local_options_file", local_options_file)
    expected_options.set_value("custom_options_file", custom_options_file)
    expected_options.set_value("results_dir", "/local/results/dir")
    expected_options.set_value("args", {"data_dir": "/local/data/dir", "extra_dir": "/custom/data/dir"})
    expected_options.set_value("yaml_options", {'default_flow_style': True, 'sort_keys': False, 'width': 100})

    assert resolved_options == expected_options


def test_resolve_user_local_custom_and_preferred_options(fixture_path):
    user_options_file = Path(fixture_path, "config_options", "user_options.yaml").as_posix()
    local_options_file = Path(fixture_path, "config_options", "local_options.yaml").as_posix()
    custom_options_file = Path(fixture_path, "config_options", "custom_options.yaml").as_posix()
    preferred_options = {
        "user_options_file": user_options_file,
        "local_options_file": local_options_file,
        "custom_options_file": custom_options_file,
        "args": {"date": "today!"}
    }
    resolved_options = resolve_config_options(preferred_options)

    expected_options = ConfigOptions()
    expected_options.set_value("user_options_file", user_options_file)
    expected_options.set_value("local_options_file", local_options_file)
    expected_options.set_value("custom_options_file", custom_options_file)
    expected_options.set_value("results_dir", "/local/results/dir")
    expected_options.set_value("args", {"data_dir": "/local/data/dir", "extra_dir": "/custom/data/dir", "date": "today!"})
    expected_options.set_value("yaml_options", {'default_flow_style': True, 'sort_keys': False, 'width': 100})

    assert resolved_options == expected_options

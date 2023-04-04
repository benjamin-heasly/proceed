from math import isnan
from pathlib import Path
from pytest import fixture
from proceed.model import Pipeline
from proceed.docker_runner import run_pipeline
from proceed.aggregator import summarize_results, collect_custom_columns


@fixture
def fixture_path(request):
    this_file = Path(request.module.__file__)
    return Path(this_file.parent, 'fixture_files')


@fixture
def pipelines(fixture_path):
    specs_paths = fixture_path.glob("*.yaml")
    pipelines = {}
    for spec_path in specs_paths:
        with open(spec_path) as f:
            spec_yaml = f.read()
        pipelines[spec_path.stem] = Pipeline.from_yaml(spec_yaml)
    return pipelines


def test_empty_results_dir(tmp_path):
    summary = summarize_results(tmp_path)
    assert summary.empty


def run(pipeline: Pipeline,
        results_dir: Path,
        results_group: str = "test_group",
        results_id: str = "test_id",
        args: dict[str, str] = {}) -> Path:
    execution_path = Path(results_dir, results_group, results_id)
    execution_path.mkdir(parents=True, exist_ok=True)
    execution_record = run_pipeline(pipeline, execution_path, args)
    out_path = Path(execution_path, "execution_record.yaml")

    with open(out_path, "w") as f:
        f.write(execution_record.to_yaml())

    return execution_path


def test_pipeline_with_error(pipelines, tmp_path):
    run(pipelines["sad_spec"], tmp_path, results_group="sad_spec")
    summary = summarize_results(tmp_path)
    assert len(summary.index) == 1
    assert summary["results_group"][0] == "sad_spec"
    assert summary["step_name"][0] == "bad"
    assert summary["step_exit_code"][0] == '1'
    assert summary["file_role"][0] == "log"
    assert summary["file_path"][0] == "bad.log"
    assert summary["file_digest"][0] == "sha256:dd23e3e2d19a110618234b282ddaa84b003d83a06a8a8b8ef301b78b68511631"


def test_only_log_file(pipelines, tmp_path):
    run(pipelines["happy_spec"], tmp_path, results_group="happy_spec")
    summary = summarize_results(tmp_path)
    assert len(summary.index) == 1
    assert summary["results_group"][0] == "happy_spec"
    assert summary["step_name"][0] == "hello"
    assert summary["step_exit_code"][0] == '0'
    assert summary["file_role"][0] == "log"
    assert summary["file_path"][0] == "hello.log"
    assert summary["file_digest"][0] == "sha256:b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c"


def test_ignore_irrelevant_yaml(pipelines, tmp_path):
    execution_path = run(pipelines["happy_spec"], tmp_path, results_group="happy_spec")

    irrelevant_path = Path(execution_path.parent, "irrelevant")
    irrelevant_path.mkdir(parents=True, exist_ok=True)
    malformed_path = Path(irrelevant_path, "execution_record.yaml")
    with open(malformed_path, "w") as f:
        f.write(",this is irrelevant, it's not even yaml!")

    summary = summarize_results(tmp_path)
    assert len(summary.index) == 1
    assert summary["results_group"][0] == "happy_spec"


def test_several_output_files(pipelines, tmp_path):
    args = {"work_dir": tmp_path.as_posix()}
    run(pipelines["files_spec"], tmp_path, results_group="files_spec", args=args)
    summary = summarize_results(tmp_path)
    assert len(summary.index) == 6
    assert summary["results_group"].to_list() == [
        "files_spec",
        "files_spec",
        "files_spec",
        "files_spec",
        "files_spec",
        "files_spec"]
    assert summary["file_role"].to_list() == [
        "log",
        "out",
        "log",
        "in",
        "out",
        "summary"]
    assert summary["file_path"].to_list() == [
        "create_file.log",
        "file.txt",
        "write_to_file.log",
        "file.txt",
        "file.txt",
        "file.txt"
    ]
    assert summary["file_digest"].to_list() == [
        "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "sha256:12a61f4e173fb3a11c05d6471f74728f76231b4a5fcd9667cef3af87a3ae4dc2",
        "sha256:12a61f4e173fb3a11c05d6471f74728f76231b4a5fcd9667cef3af87a3ae4dc2",
    ]


def test_summarize_multiple_pipelines(pipelines, tmp_path):
    args = {"work_dir": tmp_path.as_posix()}
    run(pipelines["files_spec"], tmp_path, results_group="files_spec", args=args)
    run(pipelines["sad_spec"], tmp_path, results_group="sad_spec")
    run(pipelines["happy_spec"], tmp_path, results_group="happy_spec")

    summary = summarize_results(tmp_path, sort_rows_by=["step_start"])

    assert len(summary.index) == 8
    assert summary["results_group"].to_list() == [
        "files_spec",
        "files_spec",
        "files_spec",
        "files_spec",
        "files_spec",
        "files_spec",
        "sad_spec",
        "happy_spec"
    ]
    assert summary["file_path"].to_list() == [
        "create_file.log",
        "file.txt",
        "write_to_file.log",
        "file.txt",
        "file.txt",
        "file.txt",
        "bad.log",
        "hello.log"
    ]


def test_repeat_runs_with_different_args(pipelines, tmp_path):
    args = {
        "work_dir": Path(tmp_path, "run_1").as_posix(),
        "content": "content 1"
    }
    run(pipelines["files_spec"], tmp_path, results_group="files_spec", results_id="run_1", args=args)
    args = {
        "work_dir": Path(tmp_path, "run_2").as_posix(),
        "content": "content 2"
    }
    run(pipelines["files_spec"], tmp_path, results_group="files_spec", results_id="run_2", args=args)

    summary = summarize_results(tmp_path, sort_rows_by=["step_start", "file_path"])

    assert len(summary.index) == 12
    assert summary["results_id"].to_list() == [
        "run_1",
        "run_1",
        "run_1",
        "run_1",
        "run_1",
        "run_1",
        "run_2",
        "run_2",
        "run_2",
        "run_2",
        "run_2",
        "run_2",
    ]
    assert summary["arg_content"].to_list() == [
        "content 1",
        "content 1",
        "content 1",
        "content 1",
        "content 1",
        "content 1",
        "content 2",
        "content 2",
        "content 2",
        "content 2",
        "content 2",
        "content 2",
    ]
    assert summary["file_path"].to_list() == [
        "create_file.log",
        "file.txt",
        "file.txt",
        "file.txt",
        "file.txt",
        "write_to_file.log",
        "create_file.log",
        "file.txt",
        "file.txt",
        "file.txt",
        "file.txt",
        "write_to_file.log",
    ]
    assert summary["file_digest"].to_list() == [
        'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'sha256:59e709625682d8e5a571a2b11fa44b54c393869f3a49bb67bea1802fc6937972',
        'sha256:59e709625682d8e5a571a2b11fa44b54c393869f3a49bb67bea1802fc6937972',
        'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'sha256:6f8a19765e9146cdf2bd4e4693bc2ce17705df9daa302dbd2ae5d6e052b51863',
        'sha256:6f8a19765e9146cdf2bd4e4693bc2ce17705df9daa302dbd2ae5d6e052b51863',
        'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    ]


def test_repeat_runs_with_done_files_and_skipping(pipelines, tmp_path):
    args = {"work_dir": tmp_path.as_posix()}
    run(pipelines["files_spec"], tmp_path, results_group="files_spec", results_id="run_1", args=args)
    run(pipelines["files_spec"], tmp_path, results_group="files_spec", results_id="run_2", args=args)

    summary = summarize_results(tmp_path, sort_rows_by=["step_start", "file_path"])

    assert len(summary.index) == 12
    assert summary["step_skipped"].to_list() == [
        "False",
        "False",
        "False",
        "False",
        "False",
        "False",
        "True",
        "True",
        "False",
        "False",
        "False",
        "False",
    ]
    assert summary["file_role"].to_list() == [
        "log",
        "out",
        "in",
        "out",
        "summary",
        "log",
        "log",
        "done",
        "in",
        "out",
        "summary",
        "log",
    ]
    assert summary["file_path"].to_list() == [
        "create_file.log",
        "file.txt",
        "file.txt",
        "file.txt",
        "file.txt",
        "write_to_file.log",
        "",
        "file.txt",
        "file.txt",
        "file.txt",
        "file.txt",
        "write_to_file.log",
    ]
    assert summary["file_digest"].to_list() == [
        'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'sha256:12a61f4e173fb3a11c05d6471f74728f76231b4a5fcd9667cef3af87a3ae4dc2',
        'sha256:12a61f4e173fb3a11c05d6471f74728f76231b4a5fcd9667cef3af87a3ae4dc2',
        'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        '',
        'sha256:12a61f4e173fb3a11c05d6471f74728f76231b4a5fcd9667cef3af87a3ae4dc2',
        'sha256:12a61f4e173fb3a11c05d6471f74728f76231b4a5fcd9667cef3af87a3ae4dc2',
        'sha256:12a61f4e173fb3a11c05d6471f74728f76231b4a5fcd9667cef3af87a3ae4dc2',
        'sha256:12a61f4e173fb3a11c05d6471f74728f76231b4a5fcd9667cef3af87a3ae4dc2',
        'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    ]


def test_summary_row_order(pipelines, tmp_path):
    args = {"work_dir": tmp_path.as_posix()}
    run(pipelines["files_spec"], tmp_path, results_group="files_spec", args=args)

    summary_by_digest = summarize_results(tmp_path, sort_rows_by=["file_digest"])
    assert len(summary_by_digest.index) == 6
    assert summary_by_digest["file_digest"].to_list() == [
        "sha256:12a61f4e173fb3a11c05d6471f74728f76231b4a5fcd9667cef3af87a3ae4dc2",
        "sha256:12a61f4e173fb3a11c05d6471f74728f76231b4a5fcd9667cef3af87a3ae4dc2",
        "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    ]

    summary_by_step_name = summarize_results(tmp_path, sort_rows_by=["step_name"])
    assert len(summary_by_step_name.index) == 6
    assert summary_by_step_name["step_name"].to_list() == [
        "create file",
        "create file",
        "write to file",
        "write to file",
        "write to file",
        "write to file",
    ]

    summary_by_step_name_and_file_path = summarize_results(tmp_path, sort_rows_by=["step_name", "file_path"])
    assert len(summary_by_step_name_and_file_path.index) == 6
    assert summary_by_step_name_and_file_path["step_name"].to_list() == [
        "create file",
        "create file",
        "write to file",
        "write to file",
        "write to file",
        "write to file",
    ]
    assert summary_by_step_name_and_file_path["file_path"].to_list() == [
        "create_file.log",
        "file.txt",
        "file.txt",
        "file.txt",
        "file.txt",
        "write_to_file.log",
    ]

    summary_by_step_name_and_garbage = summarize_results(tmp_path, sort_rows_by=["step_name", "garbage"])
    assert len(summary_by_step_name_and_garbage.index) == 6
    assert summary_by_step_name_and_garbage["step_name"].to_list() == [
        "create file",
        "create file",
        "write to file",
        "write to file",
        "write to file",
        "write to file",
    ]


def test_choose_summary_columns(pipelines, tmp_path):
    run(pipelines["happy_spec"], tmp_path, results_group="happy_spec")
    summary_name_and_digest = summarize_results(tmp_path, columns=["step_name", "file_digest"])
    assert len(summary_name_and_digest.index) == 1
    assert list(summary_name_and_digest.columns) == ["step_name", "file_digest"]
    assert summary_name_and_digest["step_name"][0] == "hello"

    summary_digest_and_name = summarize_results(tmp_path, columns=["file_digest", "step_name"])
    assert len(summary_digest_and_name.index) == 1
    assert list(summary_digest_and_name.columns) == ["file_digest", "step_name"]
    assert summary_digest_and_name["step_name"][0] == "hello"

    summary_name_and_garbage = summarize_results(tmp_path, columns=["step_name", "garbage"])
    assert len(summary_name_and_garbage.index) == 1
    assert list(summary_name_and_garbage.columns) == ["step_name"]
    assert summary_name_and_garbage["step_name"][0] == "hello"


def test_collect_custom_columns(fixture_path):
    file_volume = Path(fixture_path, "custom_columns").as_posix()

    no_such_file_columns = collect_custom_columns(file_volume, "no_such_file")
    assert not no_such_file_columns

    invalid_columns = collect_custom_columns(file_volume, "invalid.yaml")
    assert invalid_columns == {"invalid": ",This is not yaml!"}

    list_columns = collect_custom_columns(file_volume, "list.yaml")
    assert list_columns == {"list": '["this", "is", "a", "list"]'}

    dictionary_columns = collect_custom_columns(file_volume, "dictionary.yaml")
    assert dictionary_columns == {
        "key1": "this",
        "key2": "is",
        "key3": "a",
        "key4": "dictionary!",
    }

    json_dictionary_columns = collect_custom_columns(file_volume, "dictionary.json")
    assert json_dictionary_columns == {
        "key1": "this",
        "key2": "is",
        "key3": "a",
        "key4": "dictionary!",
    }


def test_custom_summary_column(pipelines, tmp_path):
    args = {"work_dir": tmp_path.as_posix(), "content": "plain text!"}
    run(pipelines["files_spec"], tmp_path, results_group="files_spec", args=args)
    summary = summarize_results(tmp_path)
    assert len(summary.index) == 6
    assert isnan(summary["file"][0])
    assert isnan(summary["file"][1])
    assert summary["file"][2] == "plain text!"
    assert summary["file"][3] == "plain text!"
    assert summary["file"][4] == "plain text!"
    assert summary["file"][5] == "plain text!"

    summary_columns = set(summary.columns)
    assert not "step_timing" in summary_columns
    assert not "step_log_file" in summary_columns
    assert not "step_files_done" in summary_columns
    assert not "step_files_in" in summary_columns
    assert not "step_files_out" in summary_columns
    assert not "step_files_summary" in summary_columns

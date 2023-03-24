from os import getcwd
from pathlib import Path
import docker
from pytest import fixture
from proceed.model import Pipeline, ExecutionRecord, Step, StepResult
from proceed.docker_runner import run_pipeline, run_step


@fixture
def alpine_image():
    """The alpine image must be present on the host, and/or we must be on the network."""
    client = docker.from_env()
    image = client.images.pull("alpine")
    return image


@fixture
def ubuntu_image():
    """The ubuntu image must be present on the host, and/or we must be on the network -- for gpu capability tests"""
    client = docker.from_env()
    image = client.images.pull("ubuntu")
    return image


@fixture
def fixture_path(request):
    this_file = Path(request.module.__file__).relative_to(getcwd())
    return Path(this_file.parent, 'fixture_files')


def read_step_logs(step_result: StepResult) -> str:
    with open(step_result.log_file, 'r') as f:
        return f.read()


def test_step_image_not_found(tmp_path):
    step = Step(name="image not found", image="no_such_image")
    step_result = run_step(step, Path(tmp_path, "step.log"))
    assert step_result.name == step.name
    assert step_result.image_id == None
    assert step_result.exit_code == None
    assert "no_such_image, repository does not exist" in read_step_logs(step_result)


def test_step_command_not_found(alpine_image, tmp_path):
    step = Step(name="command not found", image=alpine_image.tags[0], command=["no_such_command"])
    step_result = run_step(step, Path(tmp_path, "step.log"))
    assert step_result.name == step.name
    assert step_result.image_id == None
    assert step_result.exit_code == None
    assert '"no_such_command": executable file not found' in read_step_logs(step_result)


def test_step_command_error(alpine_image, tmp_path):
    step = Step(name="command error", image=alpine_image.tags[0], command=["ls", "no_such_dir"])
    step_result = run_step(step, Path(tmp_path, "step.log"))
    assert step_result.name == step.name
    assert step_result.image_id == alpine_image.id
    assert step_result.exit_code == 1
    assert "no_such_dir: No such file or directory" in read_step_logs(step_result)


def test_step_command_success(alpine_image, tmp_path):
    step = Step(name="command success", image=alpine_image.tags[0], command=["echo", "hello to you"])
    step_result = run_step(step, Path(tmp_path, "step.log"))
    assert step_result.name == step.name
    assert step_result.image_id == alpine_image.id
    assert step_result.exit_code == 0
    assert "hello to you" in read_step_logs(step_result)


def test_step_working_dir(alpine_image, tmp_path):
    step = Step(name="working dir", working_dir="/home", image=alpine_image.tags[0], command=["pwd"])
    step_result = run_step(step, Path(tmp_path, "step.log"))
    assert step_result.name == step.name
    assert step_result.image_id == alpine_image.id
    assert step_result.exit_code == 0
    assert read_step_logs(step_result) == "/home\n"


def test_step_environment(alpine_image, tmp_path):
    step = Step(
        name="environment",
        environment={"ENV_VAR": "foo"},
        image=alpine_image.tags[0],
        command=["/bin/sh", "-c", "echo $ENV_VAR"]
    )
    step_result = run_step(step, Path(tmp_path, "step.log"))
    assert step_result.name == step.name
    assert step_result.image_id == alpine_image.id
    assert step_result.exit_code == 0
    assert read_step_logs(step_result) == "foo\n"


def test_step_network_mode_none(alpine_image, tmp_path):
    step = Step(
        name="network mode none",
        network_mode="none",
        image=alpine_image.tags[0],
        command=["ifconfig"]
    )
    step_result = run_step(step, Path(tmp_path, "step.log"))
    assert step_result.name == step.name
    assert step_result.image_id == alpine_image.id
    assert step_result.exit_code == 0
    assert "eth0" not in read_step_logs(step_result)


def test_step_network_mode_bridge(alpine_image, tmp_path):
    step = Step(
        name="network mode bridge",
        network_mode="bridge",
        image=alpine_image.tags[0],
        command=["ifconfig"]
    )
    step_result = run_step(step, Path(tmp_path, "step.log"))
    assert step_result.name == step.name
    assert step_result.image_id == alpine_image.id
    assert step_result.exit_code == 0
    assert "eth0" in read_step_logs(step_result)


def test_step_mac_address(alpine_image, tmp_path):
    step = Step(
        name="mac address",
        mac_address="aa:bb:cc:dd:ee:ff",
        image=alpine_image.tags[0],
        command=["ifconfig"]
    )
    step_result = run_step(step, Path(tmp_path, "step.log"))
    assert step_result.name == step.name
    assert step_result.image_id == alpine_image.id
    assert step_result.exit_code == 0
    assert "HWaddr AA:BB:CC:DD:EE:FF" in read_step_logs(step_result)


def test_step_gpus(ubuntu_image, tmp_path):
    # The ubuntu image, but not alpine, provides the "nvidia-smi" utility we want.
    step = Step(
        name="gpus",
        gpus=True,
        image=ubuntu_image.tags[0],
        command=["nvidia-smi"]
    )
    step_result = run_step(step, Path(tmp_path, "step.log"))
    assert step_result.name == step.name

    # Awkwardly, the result of this test depends on whether the host has docker "--gpus" support.
    # For this test we want to know whether we correctly *requested* a gpu device.
    # We don't actually care if the process was able to use a gpu.
    # So, we'll check for two expected outcomes, assuming we at least *requested* the gpu.
    if step_result.exit_code == 0: # pragma: no cover
        # This is actually the unusual case for testing on laptops, github actions, etc.
        # So we don't ask pytest-cov to track coverage for this branch.

        # Host seems to have docker "--gpus" support.
        assert step_result.timing._is_complete()
        assert "NVIDIA-SMI" in read_step_logs(step_result)
    else:
        # Host seems not to have docker "--gpus" support, check for relevant error, as in:
        # https://github.com/NVIDIA/nvidia-docker/issues/1034
        assert not step_result.timing._is_complete()
        assert 'could not select device driver "" with capabilities: [[gpu]]' in read_step_logs(step_result)


def test_step_files_done(alpine_image, fixture_path, tmp_path):
    fixture_dir = fixture_path.as_posix()
    step = Step(
        name="files done",
        image=alpine_image.tags[0],
        command=["echo 'this should be skipped'"],
        volumes={fixture_dir: "/fixture_files"},
        match_done=["*.yaml", "*.ignore"]
    )
    step_result = run_step(step, Path(tmp_path, "step.log"))

    # The runner should find yaml files in the working dir, "tests/proceed/fixture_files".
    # The existence of these files should cause the step itself to be skipped.
    expected_files = {
        fixture_dir: {
            "files_spec.yaml": "sha256:1423a32c9cfa52022f98843ee679ceac18e5cabd34824b6a558de694abff2319",
            "happy_spec.yaml": "sha256:23b5688d1593f8479a42dad99efa791db4bf795de9330a06664ac22837fc3ecc",
            "sad_spec.yaml": "sha256:cc428c52c6c015b4680559a540cf0af5c3e7878cd711109b7f0fe0336e40b000",
        }
    }
    assert step_result.files_done == expected_files
    assert not step_result.files_in
    assert not step_result.files_out
    assert step_result.skipped
    assert step_result.exit_code is None
    assert not step_result.log_file


def test_step_files_in(alpine_image, fixture_path, tmp_path):
    fixture_dir = fixture_path.as_posix()
    step = Step(
        name="files in",
        image=alpine_image.tags[0],
        command=["echo", "hello files in"],
        volumes={fixture_dir: "/fixture_files"},
        match_in=["*.yaml", "*.ignore"]
    )
    step_result = run_step(step, Path(tmp_path, "step.log"))

    # The runner should find yaml files in the working dir, "tests/proceed/fixture_files".
    # The existence of these files should be noted, and the step should run normally.
    expected_files = {
        fixture_dir: {
            "files_spec.yaml": "sha256:1423a32c9cfa52022f98843ee679ceac18e5cabd34824b6a558de694abff2319",
            "happy_spec.yaml": "sha256:23b5688d1593f8479a42dad99efa791db4bf795de9330a06664ac22837fc3ecc",
            "sad_spec.yaml": "sha256:cc428c52c6c015b4680559a540cf0af5c3e7878cd711109b7f0fe0336e40b000",
        }
    }
    assert step_result.exit_code == 0
    assert read_step_logs(step_result) == "hello files in\n"
    assert step_result.files_in == expected_files
    assert not step_result.files_done
    assert not step_result.files_out
    assert not step_result.skipped


def test_step_files_out(alpine_image, fixture_path, tmp_path):
    fixture_dir = fixture_path.as_posix()
    step = Step(
        name="files out",
        image=alpine_image.tags[0],
        command=["echo", "hello files out"],
        volumes={fixture_dir: "/fixture_files"},
        match_out=["*.yaml", "*.ignore"]
    )
    step_result = run_step(step, Path(tmp_path, "step.log"))

    # The runner should find yaml files in the working dir, "tests/proceed/fixture_files".
    # The existence of these files should be noted, and the step should run normally.
    expected_files = {
        fixture_dir: {
            "files_spec.yaml": "sha256:1423a32c9cfa52022f98843ee679ceac18e5cabd34824b6a558de694abff2319",
            "happy_spec.yaml": "sha256:23b5688d1593f8479a42dad99efa791db4bf795de9330a06664ac22837fc3ecc",
            "sad_spec.yaml": "sha256:cc428c52c6c015b4680559a540cf0af5c3e7878cd711109b7f0fe0336e40b000",
        }
    }
    assert step_result.exit_code == 0
    assert read_step_logs(step_result) == "hello files out\n"
    assert step_result.files_out == expected_files
    assert not step_result.files_in
    assert not step_result.files_done
    assert not step_result.skipped


def test_pipeline_with_args(alpine_image, tmp_path):
    pipeline = Pipeline(
        args={
            "arg_1": "foo",
            "arg_2": "bar"
        },
        steps=[
            Step(name="step 1", image=alpine_image.tags[0], command=["echo", "hello $arg_1"]),
            Step(name="step 2", image=alpine_image.tags[0], command=["echo", "hello $arg_2"])
        ]
    )
    args = {
        "ignored": "ignore me",
        "arg_1": "quux"
    }
    pipeline_result = run_pipeline(pipeline, tmp_path, args)
    expected_amended = Pipeline(
        args={
            "arg_1": "quux",
            "arg_2": "bar"
        },
        steps=[
            Step(name="step 1", image=alpine_image.tags[0], command=["echo", "hello quux"]),
            Step(name="step 2", image=alpine_image.tags[0], command=["echo", "hello bar"])
        ]
    )
    expected_step_results = [
        StepResult(name="step 1", image_id=alpine_image.id, exit_code=0, log_file=Path(tmp_path, "step_1.log").as_posix()),
        StepResult(name="step 2", image_id=alpine_image.id, exit_code=0, log_file=Path(tmp_path, "step_2.log").as_posix())
    ]
    expected_result = ExecutionRecord(
        original=pipeline,
        amended=expected_amended,
        step_results=expected_step_results
    )
    assert pipeline_result == expected_result

    # Timing details are not used in comparisons above -- timestamps are too brittle.
    # But we do want to check that timing results got filled in.
    assert pipeline_result.timing._is_complete()
    assert all([step_result.timing._is_complete() for step_result in pipeline_result.step_results])

    assert read_step_logs(pipeline_result.step_results[0]) == "hello quux\n"
    assert read_step_logs(pipeline_result.step_results[1]) == "hello bar\n"


def test_pipeline_with_environment(alpine_image, tmp_path):
    pipeline = Pipeline(
        prototype=Step(
            environment={
                "env_1": "one",
                "env_2": "two"
            }
        ),
        steps=[
            Step(
                name="step 1",
                image=alpine_image.tags[0],
                environment={"env_2": "two-a", "env_3": "three-a"},
                command=["/bin/sh", "-c", "echo $env_1 $env_2 $env_3"]
            ),
            Step(
                name="step 2",
                image=alpine_image.tags[0],
                environment={"env_2": "two-b", "env_3": "three-b"},
                command=["/bin/sh", "-c", "echo $env_1 $env_2 $env_3"]
            )
        ]
    )
    pipeline_result = run_pipeline(pipeline, tmp_path)
    expected_step_results = [
        StepResult(name="step 1", image_id=alpine_image.id, exit_code=0, log_file=Path(tmp_path, "step_1.log").as_posix()),
        StepResult(name="step 2", image_id=alpine_image.id, exit_code=0, log_file=Path(tmp_path, "step_2.log").as_posix())
    ]
    expected_result = ExecutionRecord(
        original=pipeline,
        amended=pipeline._with_prototype_applied(),
        step_results=expected_step_results
    )
    assert pipeline_result == expected_result
    assert pipeline_result.timing._is_complete()
    assert all([step_result.timing._is_complete() for step_result in pipeline_result.step_results])

    assert read_step_logs(pipeline_result.step_results[0]) == "one two-a three-a\n"
    assert read_step_logs(pipeline_result.step_results[1]) == "one two-b three-b\n"


def test_pipeline_with_network_config(alpine_image, tmp_path):
    pipeline = Pipeline(
        prototype=Step(
            network_mode="none",
            mac_address="11:22:33:44:55:66"
        ),
        steps=[
            Step(
                name="step 1",
                image=alpine_image.tags[0],
                network_mode="bridge",
                mac_address="aa:bb:cc:dd:ee:ff",
                command=["ifconfig"]
            ),
            Step(
                name="step 2",
                image=alpine_image.tags[0],
                command=["ifconfig"]
            )
        ]
    )
    pipeline_result = run_pipeline(pipeline, tmp_path)

    # First step should override the pipeline's network config.
    assert pipeline_result.step_results[0].name == pipeline.steps[0].name
    assert pipeline_result.step_results[0].image_id == alpine_image.id
    assert pipeline_result.step_results[0].exit_code == 0
    assert "eth0" in read_step_logs(pipeline_result.step_results[0])
    assert "HWaddr AA:BB:CC:DD:EE:FF" in read_step_logs(pipeline_result.step_results[0])

    # Second step should inherit the pipeline's network config.
    assert pipeline_result.step_results[1].name == pipeline.steps[1].name
    assert pipeline_result.step_results[1].image_id == alpine_image.id
    assert pipeline_result.step_results[1].exit_code == 0
    assert "eth0" not in read_step_logs(pipeline_result.step_results[1])
    assert "HWaddr" not in read_step_logs(pipeline_result.step_results[1])

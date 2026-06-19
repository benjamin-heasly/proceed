from pathlib import Path

from pytest import fixture

from proceed.model import Pipeline, Step
from proceed.run_recorder import RunRecorder
from proceed.runner_protocol import run_pipeline, run_step
from proceed.slurm_runner import SlurmRunner


@fixture
def success_runner():
    # Always succeed and log arguments intended for srun.
    return SlurmRunner(srun_path='/usr/bin/echo')

@fixture
def failure_runner():
    # Always fail.
    return SlurmRunner(srun_path='/usr/bin/false')


def test_step_command_success(success_runner, tmp_path):
    step = Step(name="hello", image="alpine:latest", command=["echo", "hello"])
    step_result = run_step(step, Path(tmp_path, "step.log"), success_runner)
    assert step_result.exit_code == 0
    assert step_result.image_id == "alpine:latest"
    assert step_result.timing._is_complete()


def test_step_command_error(failure_runner, tmp_path):
    step = Step(name="fail", image="alpine:latest", command=["false"])
    step_result = run_step(step, Path(tmp_path, "step.log"), failure_runner)
    assert step_result.exit_code == 1
    assert step_result.image_id == "alpine:latest"


def test_step_srun_not_found(tmp_path):
    runner = SlurmRunner(srun_path="/no/such/srun")
    step = Step(name="missing srun", image="alpine:latest", command=["echo", "hi"])
    step_result = run_step(step, Path(tmp_path, "step.log"), runner)
    assert step_result.exit_code == -1
    assert step_result.image_id is None
    with open(step_result.log_file) as f:
        logs = f.read()
    assert "FileNotFoundError" in logs


def test_step_image_arg(success_runner, tmp_path):
    step = Step(name="img", image="nvcr.io/nvidia/cuda:12.0-base", command=["nvidia-smi"])
    step_result = run_step(step, Path(tmp_path, "step.log"), success_runner)
    assert step_result.exit_code == 0
    assert step_result.image_id == "nvcr.io/nvidia/cuda:12.0-base"
    assert step_result.timing._is_complete()
    with open(step_result.log_file) as f:
        logs = f.read()
    assert "--container-image=nvcr.io/nvidia/cuda:12.0-base" in logs


def test_step_command_args(success_runner, tmp_path):
    step = Step(name="cmd", image="alpine:latest", command=["echo", "hello world"])
    step_result = run_step(step, Path(tmp_path, "step.log"), success_runner)
    assert step_result.exit_code == 0
    assert step_result.image_id == "alpine:latest"
    assert step_result.timing._is_complete()
    with open(step_result.log_file) as f:
        logs = f.read()
    assert "echo" in logs
    assert "hello world" in logs


def test_step_volumes(success_runner, tmp_path):
    host_dir = tmp_path / "data"
    host_dir.mkdir()
    step = Step(
        name="vols",
        image="alpine:latest",
        volumes={str(host_dir): "/data"},
        command=["ls"],
    )
    step_result = run_step(step, Path(tmp_path, "step.log"), success_runner)
    assert step_result.exit_code == 0
    assert step_result.image_id == "alpine:latest"
    assert step_result.timing._is_complete()
    with open(step_result.log_file) as f:
        logs = f.read()
    assert f"--container-mounts={host_dir}:/data" in logs


def test_step_readonly_volume_warns(success_runner, tmp_path, caplog):
    import logging
    host_dir = tmp_path / "data"
    host_dir.mkdir()
    step = Step(
        name="read-only volume",
        image="alpine:latest",
        volumes={str(host_dir): {"bind": "/data", "mode": "ro"}},
        command=["ls"],
    )
    with caplog.at_level(logging.WARNING):
        step_result = run_step(step, Path(tmp_path, "step.log"), success_runner)
    assert "ignoring read-only" in caplog.messages[0]

    # Mount should still be present even though ro is unsupported.
    assert step_result.exit_code == 0
    assert step_result.image_id == "alpine:latest"
    assert step_result.timing._is_complete()
    with open(step_result.log_file) as f:
        logs = f.read()
    assert f"--container-mounts={host_dir}:/data" in logs


def test_step_working_dir(success_runner, tmp_path):
    step = Step(name="wd", image="alpine:latest", working_dir="/work", command=["pwd"])
    step_result = run_step(step, Path(tmp_path, "step.log"), success_runner)
    assert step_result.exit_code == 0
    assert step_result.image_id == "alpine:latest"
    assert step_result.timing._is_complete()
    with open(step_result.log_file) as f:
        logs = f.read()
    assert f"--container-workdir=/work" in logs


def test_step_environment(success_runner, tmp_path):
    step = Step(
        name="env",
        image="alpine:latest",
        environment={"FOO": "bar", "BAZ": "quux"},
        command=["env"],
    )
    step_result = run_step(step, Path(tmp_path, "step.log"), success_runner)
    assert step_result.exit_code == 0
    assert step_result.image_id == "alpine:latest"
    assert step_result.timing._is_complete()
    with open(step_result.log_file) as f:
        logs = f.read()
    assert f"--export=FOO=bar" in logs
    assert f"--export=BAZ=quux" in logs


def test_step_gpus_all(success_runner, tmp_path):
    step = Step(name="gpus", image="ubuntu:latest", gpus=True, command=["nvidia-smi"])
    step_result = run_step(step, Path(tmp_path, "step.log"), success_runner)
    assert step_result.exit_code == 0
    assert step_result.image_id == "ubuntu:latest"
    assert step_result.timing._is_complete()
    with open(step_result.log_file) as f:
        logs = f.read()
    assert "--gpus-per-node=1" in logs


def test_step_gpus_one_device(success_runner, tmp_path):
    step = Step(name="gpus", image="ubuntu:latest", gpus="my-gpu", command=["nvidia-smi"])
    step_result = run_step(step, Path(tmp_path, "step.log"), success_runner)
    assert step_result.exit_code == 0
    assert step_result.image_id == "ubuntu:latest"
    assert step_result.timing._is_complete()
    with open(step_result.log_file) as f:
        logs = f.read()
    assert "--gpus-per-node=my-gpu" in logs


def test_step_gpus_one_number(success_runner, tmp_path):
    step = Step(name="gpus", image="ubuntu:latest", gpus=2, command=["nvidia-smi"])
    step_result = run_step(step, Path(tmp_path, "step.log"), success_runner)
    assert step_result.exit_code == 0
    assert step_result.image_id == "ubuntu:latest"
    assert step_result.timing._is_complete()
    with open(step_result.log_file) as f:
        logs = f.read()
    assert "--gpus-per-node=2" in logs


def test_step_gpus_list(success_runner, tmp_path):
    step = Step(name="gpus", image="ubuntu:latest", gpus=["my-gpu:1", 42], command=["nvidia-smi"])
    step_result = run_step(step, Path(tmp_path, "step.log"), success_runner)
    assert step_result.exit_code == 0
    assert step_result.image_id == "ubuntu:latest"
    assert step_result.timing._is_complete()
    with open(step_result.log_file) as f:
        logs = f.read()
    assert "--gpus-per-node=my-gpu:1,42" in logs


def test_step_docker_only_fields_warn(success_runner, tmp_path, caplog):
    import logging
    step = Step(
        name="docker fields",
        image="alpine:latest",
        mac_address="aa:bb:cc:dd:ee:ff",
        network_mode="bridge",
        privileged=True,
        shm_size="2g",
        user="self",
        command=["id"],
    )
    with caplog.at_level(logging.WARNING):
        run_step(step, Path(tmp_path, "step.log"), success_runner)

    assert "Step 'docker fields': field 'mac_address' is not supported by the Slurm runner and will be ignored." in caplog.messages
    assert "Step 'docker fields': field 'network_mode' is not supported by the Slurm runner and will be ignored." in caplog.messages
    assert "Step 'docker fields': field 'privileged' is not supported by the Slurm runner and will be ignored." in caplog.messages
    assert "Step 'docker fields': field 'shm_size' is not supported by the Slurm runner and will be ignored." in caplog.messages
    assert "Step 'docker fields': field 'user' is not supported by the Slurm runner and will be ignored." in caplog.messages


def test_pipeline_two_steps(success_runner, tmp_path):
    pipeline = Pipeline(
        steps=[
            Step(name="step 1", image="alpine:latest", command=["echo", "one"]),
            Step(name="step 2", image="ubuntu:latest", command=["echo", "two"]),
        ]
    )
    run_recorder = RunRecorder(tmp_path)
    pipeline_result = run_pipeline(pipeline, tmp_path, run_recorder, success_runner)
    assert len(pipeline_result.step_results) == 2

    assert pipeline_result.step_results[0].exit_code == 0
    assert pipeline_result.step_results[0].image_id == "alpine:latest"
    assert pipeline_result.step_results[0].timing._is_complete()
    with open(pipeline_result.step_results[0].log_file) as f:
        logs_0 = f.read()
    assert "echo one" in logs_0

    assert pipeline_result.step_results[1].exit_code == 0
    assert pipeline_result.step_results[1].image_id == "ubuntu:latest"
    assert pipeline_result.step_results[1].timing._is_complete()
    with open(pipeline_result.step_results[1].log_file) as f:
        logs_1 = f.read()
    assert "echo two" in logs_1


def test_pipeline_stops_on_error(failure_runner, tmp_path):
    pipeline = Pipeline(
        steps=[
            Step(name="fail", image="alpine:latest", command=["false"]),
            Step(name="should not run", image="alpine:latest", command=["echo", "hi"]),
        ]
    )
    run_recorder = RunRecorder(tmp_path)
    pipeline_result = run_pipeline(pipeline, tmp_path, run_recorder, failure_runner)

    assert len(pipeline_result.step_results) == 1
    assert pipeline_result.step_results[0].exit_code == 1
    assert pipeline_result.step_results[0].image_id == "alpine:latest"
    assert pipeline_result.step_results[0].timing._is_complete()

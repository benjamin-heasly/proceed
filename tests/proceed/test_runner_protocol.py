from os import environ

from proceed.runner_protocol import make_runner, discover_runner
from proceed.docker_runner import DockerRunner
from proceed.slurm_runner import SlurmRunner


def test_make_docker_runner():
    runner = make_runner("docker")
    assert isinstance(runner, DockerRunner)


def test_make_slurm_runner():
    runner = make_runner("slurm")
    assert isinstance(runner, SlurmRunner)


def test_make_unknown_runner():
    runner = make_runner("NOPE")
    assert runner is None


def test_discover_docker_runner():
    runner = discover_runner(docker_environment=environ, slurm_srun_path=None)
    assert isinstance(runner, DockerRunner)


def test_discover_slurm_runner():
    runner = discover_runner(docker_environment=None, slurm_srun_path="/usr/bin/true")
    assert isinstance(runner, SlurmRunner)


def test_discover_no_runners():
    runner = discover_runner(docker_environment=None, slurm_srun_path=None)
    assert runner is None


def test_discover_no_runners_no_docker_daemon():
    docker_environment = {
        "DOCKER_HOST": "NOPE"
    }
    runner = discover_runner(docker_environment=docker_environment, slurm_srun_path=None)
    assert runner is None

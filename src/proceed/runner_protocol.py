import logging
import shutil
from os import environ
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, runtime_checkable

from proceed.model import Pipeline, ExecutionRecord, Step, StepResult, Timing
from proceed.run_recorder import RunRecorder
from proceed.file_matching import count_matches, match_patterns_in_dirs


@runtime_checkable
class Runner(Protocol):
    """Protocol that all proceed execution backends must implement."""

    def run_container(
        self,
        step: Step,
        log_path: Path,
    ) -> tuple[str | None, int, str | None]:
        """Run one container step.

        Returns:
            image_id: identifier for the image that ran, or None on error
            exit_code: process exit code, or -1 on error
            error_message: formatted error string on failure, or None on success
        """
        ...


def apply_step_X11(step: Step) -> Step:
    """Set up the step as an X11 gui client with DISPLAY access.

    This is implemented here in the docker_runner and not in the model
    because the intended behavior depends on the runtime system and environment.
    """
    if not step.X11:
        return

    if "DISPLAY" not in step.environment:
        display = environ.get("DISPLAY")
        logging.info(f"Step '{step.name}': using X11 DISPLAY: {display}")
        step.environment["DISPLAY"] = display

    local_socket_dir = "/tmp/.X11-unix"
    if local_socket_dir not in step.volumes:
        logging.info(f"Step '{step.name}': using X11 local socket dir: {local_socket_dir}")
        step.volumes[local_socket_dir] = local_socket_dir

    if step.network_mode is None:
        logging.info(f"Step '{step.name}': using network_mode host for X11 support")
        step.network_mode = "host"

    default_xauthority = "~/.Xauthority"
    xauthority = environ.get("XAUTHORITY", default_xauthority)
    from pathlib import Path as _Path
    xauthorith_path = _Path(xauthority).expanduser().absolute()
    logging.info(f"Step '{step.name}': looking for .Xauthority cookie file at {xauthority} AKA {xauthorith_path}")
    if xauthorith_path.exists():
        xauthority_host = xauthorith_path.as_posix()
        logging.info(f"Step '{step.name}': found .Xauthority cookie file on host at {xauthority_host}")

        xauthority_container = "/var/.Xauthority"
        if xauthority_host not in step.volumes:
            logging.info(f"Step '{step.name}': adding .Xauthority cookie file to container at {xauthority_container}")
            step.volumes[xauthority_host] = xauthority_container

        if "XAUTHORITY" not in step.environment:
            logging.info(f"Step '{step.name}': setting XAUTHORITY env var in container to {xauthority_container}")
            step.environment["XAUTHORITY"] = xauthority_container

    return step


def run_step(
    step: Step,
    log_path: Path,
    runner: Runner,
    force_rerun: bool = False,
) -> StepResult:
    """Run one step using the given runner and return its result."""
    logging.info(f"Step '{step.name}': starting.")

    start = datetime.now(timezone.utc)
    start_iso = start.isoformat(sep="T")

    # Create volume dirs on the host as the current user before the container tries to mount them.
    volume_dirs = step.volumes.keys()
    for volume_dir in volume_dirs:
        volume_path = Path(volume_dir)
        if not volume_path.exists():
            logging.info(f"Step '{step.name}': creating host directory: {volume_path}")
            volume_path.mkdir(parents=True, exist_ok=True)

    if step.progress_file is not None:
        progress_done_file = Path(step.progress_file + ".done")
        if progress_done_file.exists():
            logging.info(f"Step '{step.name}': found progress .done file {progress_done_file}.")
            if force_rerun:
                logging.info(f"Step '{step.name}': executing despite .done file because force_rerun is {force_rerun}.")
            else:
                logging.info(f"Step '{step.name}': skipping execution because .done file found {progress_done_file}.")
                return StepResult(
                    name=step.name,
                    skipped=True,
                    progress_done_file=progress_done_file.as_posix(),
                    timing=Timing(start_iso)
                )

    files_done = match_patterns_in_dirs(volume_dirs, step.match_done)
    if files_done:
        logging.info(f"Step '{step.name}': found {count_matches(files_done)} done files.")
        if force_rerun:
            logging.info(f"Step '{step.name}': executing despite done files because force_rerun is {force_rerun}.")
        else:
            logging.info(f"Step '{step.name}': skipping execution because done files were found.")
            return StepResult(
                name=step.name,
                skipped=True,
                files_done=files_done,
                timing=Timing(start_iso)
            )

    if step.progress_file is not None:
        progress_file = Path(step.progress_file)
        progress_file.parent.mkdir(parents=True, exist_ok=True)
        with open(progress_file, "w") as f:
            f.write(f"{start_iso} Starting step {step.name}\n")

    files_in = match_patterns_in_dirs(volume_dirs, step.match_in)
    logging.info(f"Step '{step.name}': found {count_matches(files_in)} input files.")

    apply_step_X11(step)

    (image_id, exit_code, error_message) = runner.run_container(step, log_path)
    finish = datetime.now(timezone.utc)
    finish_iso = finish.isoformat(sep="T")

    if error_message is not None:
        with open(log_path, 'a') as f:
            f.write(error_message)
        logging.error(f"Step '{step.name}': error (see stack trace above) {error_message}")
        return StepResult(
            name=step.name,
            log_file=log_path.as_posix(),
            timing=Timing(start_iso),
            exit_code=exit_code
        )

    files_out = match_patterns_in_dirs(volume_dirs, step.match_out)
    logging.info(f"Step '{step.name}': found {count_matches(files_out)} output files.")

    files_summary = match_patterns_in_dirs(volume_dirs, step.match_summary)
    logging.info(f"Step '{step.name}': found {count_matches(files_summary)} summary files.")

    if step.progress_file is not None:
        progress_file = Path(step.progress_file)
        if exit_code == 0:
            with open(progress_file, "a") as f:
                f.write(f"{finish_iso} exit code {exit_code}\n")
                f.write(f"{finish_iso} completed step {step.name}\n")
            progress_file.rename(step.progress_file + ".done")
            logging.info(f"Step '{step.name}': renamed {progress_file} to {progress_done_file}.")
        else:
            with open(progress_file, "a") as f:
                f.write(f"{finish_iso} exit code {exit_code}\n")
                f.write(f"{finish_iso} error in step {step.name}\n")

    logging.info(f"Step '{step.name}': finished.")
    duration = finish - start
    return StepResult(
        name=step.name,
        image_id=image_id,
        exit_code=exit_code,
        log_file=log_path.as_posix(),
        files_done=files_done,
        files_in=files_in,
        files_out=files_out,
        files_summary=files_summary,
        timing=Timing(start.isoformat(sep="T"), finish.isoformat(sep="T"), duration.total_seconds()),
    )


def run_pipeline(
    original: Pipeline,
    execution_path: Path,
    run_recorder: RunRecorder,
    runner: Runner,
    args: dict[str, str] = {},
    force_rerun: bool = False,
    step_names: list[str] = None,
) -> ExecutionRecord:
    """Run steps of a pipeline and return results.

    :param original: a Pipeline, as read from an input YAML spec
    :param runner: a Runner that executes each step's container
    :return: a summary of Pipeline execution results.
    """
    logging.info("Starting pipeline run.")

    start = datetime.now(timezone.utc)
    start_iso = start.isoformat(sep="T")

    amended = original._with_args_applied(args)._with_prototype_applied()
    step_results = []
    try:
        for step in amended.steps:
            if step_names and not step.name in step_names:
                logging.info(f"Ignoring step '{step.name}', not in list of steps to run: {step_names}")
                continue

            log_stem = step.name.replace(" ", "_")
            log_path = Path(execution_path, f"{log_stem}.log")

            # Write a partial record before running so a crash still leaves a breadcrumb.
            partial_result = StepResult(
                name=step.name,
                log_file=log_path.as_posix(),
                timing=Timing(start_iso)
            )
            step_results.append(partial_result)
            partial_record = ExecutionRecord(
                original=original,
                amended=amended,
                step_results=step_results,
                timing=Timing(start_iso)
            )
            run_recorder.write(partial_record)

            step_result = run_step(step, log_path, runner, force_rerun)
            step_results[-1] = step_result

            if step_result.exit_code:
                logging.error("Stopping pipeline run after error.")
                break

    finally:
        finish = datetime.now(timezone.utc)
        finish_iso = finish.isoformat(sep="T")
        duration = finish - start

        logging.info("Finished pipeline run.")

        execution_record = ExecutionRecord(
            original=original,
            amended=amended,
            step_results=step_results,
            timing=Timing(start_iso, finish_iso, duration.total_seconds())
        )
        run_recorder.write(execution_record)

    return execution_record


def make_runner(runner_name: str, **kwargs) -> Runner|None:
    """Construct a Runner by name.

    Lazy imports prevent ImportError -- eg don't try to import docker on a slurm-only system.
    """
    if runner_name == "docker":
        from proceed.docker_runner import DockerRunner
        return DockerRunner(**kwargs)
    elif runner_name == "slurm":
        from proceed.slurm_runner import SlurmRunner
        return SlurmRunner(**kwargs)
    else:
        logging.error(f"Unknown runner: {runner_name!r}. Choose 'docker' or 'slurm'.")
        return None


def discover_runner(
    docker_environment: dict[str, str] = environ,
    slurm_srun_path: str = "srun"
) -> Runner|None:
    """Return the first available runner, preferring Docker over Slurm.

    Docker is confirmed by pinging the daemon (not just finding the CLI).
    Slurm is confirmed by finding srun on PATH.
    """
    if docker_environment:
        try:
            from docker import from_env
            client = from_env(environment=docker_environment)
            client.ping()
            logging.info("Detected docker backend (daemon is running).")
            from proceed.docker_runner import DockerRunner
            return DockerRunner()
        except Exception:
            logging.info("Docker runner not available (daemon not running or docker SDK not installed).")

    if slurm_srun_path and shutil.which(slurm_srun_path) is not None:
        logging.info(f"Detected slurm backend ({slurm_srun_path} found on PATH).")
        from proceed.slurm_runner import SlurmRunner
        return SlurmRunner(srun_path=slurm_srun_path)

    logging.error("No backend detected: Docker nor Slurm.")
    return None

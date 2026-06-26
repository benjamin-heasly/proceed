import logging
import subprocess
from pathlib import Path
from typing import Union

from proceed.model import Step
from proceed.runner_protocol import apply_step_X11


def _mounts_from_volumes(
    volumes: dict[str, Union[str, dict[str, str]]]
) -> list[tuple[str, str, str]]:
    """Convert a volumes dict to (host_abs, container_abs, mode) tuples."""
    mounts = []
    for host_path, volume in volumes.items():
        host_abs = Path(host_path).absolute().as_posix()
        if isinstance(volume, str):
            mounts.append((host_abs, Path(volume).absolute().as_posix(), "rw"))
        else:
            mode = volume.get("mode", "rw")
            mounts.append((host_abs, Path(volume["bind"]).absolute().as_posix(), mode))
    return mounts


class SlurmRunner:
    """Execute pipeline steps via srun with Pyxis/Enroot container support."""

    def __init__(
        self,
        srun_path: str = "srun"
    ):
        self.srun_path = srun_path

    def run_container(
        self,
        step: Step,
        log_path: Path,
    ) -> tuple[str | None, int, str | None]:
        """Run one step via srun with Pyxis/Enroot.

        Returns (image_id, exit_code, error_message). On success error_message is None.
        The image_id is set to the step's image string to record what was requested.
        """
        self._warn_unsupported_fields(step)

        # Don't try to mount ~/.Xauthority on Slurm, instead use pyxis "--container-mount-home" below.
        apply_step_X11(step, mount_and_set_xauthority=False)

        args = self._build_srun_args(step)
        logging.info(f"Step '{step.name}': running srun command: {args}")

        try:
            process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            with open(log_path, 'w') as f:
                for log_entry in process.stdout:
                    f.write(log_entry)
                    logging.info(f"Step '{step.name}': {log_entry.strip()}\r")

            return_code = process.wait()
            logging.info(f"Step '{step.name}': completed with exit code {return_code}.")
            return (step.image, return_code, None)

        except Exception as e:
            error_message = f"{type(e).__name__}: {e.args}\n"
            logging.error(f"Step '{step.name}': {error_message}", exc_info=True)
            return (None, -1, error_message)

    def _warn_unsupported_fields(self, step: Step) -> None:
        """Warn about Step fields that are not used with Slurm/Pyxis equivalent."""
        unsupported_fields = {
            "mac_address": step.mac_address,
            "network_mode": step.network_mode,
            "privileged": step.privileged,
            "shm_size": step.shm_size,
            "user": step.user
        }
        for field_name, value in unsupported_fields.items():
            if value:
                logging.warning(f"Step '{step.name}': '{field_name}' is ignored by Slurm runner.")

    def _build_srun_args(self, step: Step) -> list[str]:
        """Build the srun argument list for the given step."""
        args = [
            self.srun_path,
            f"--container-image={step.image}"
        ]

        if step.X11:
            # Give the container access to eg ~/.Xauthority
            args.append("--container-mount-home")

        mounts = _mounts_from_volumes(step.volumes)
        if mounts:
            container_mounts = [f"{host}:{container}:{mode}" for host, container, mode in mounts]
            container_mounts_arg = ",".join(container_mounts)
            args.append(f"--container-mounts={container_mounts_arg}")

        if step.working_dir:
            args.append(f"--container-workdir={step.working_dir}")

        for key, value in step.environment.items():
            args.append(f"--export={key}={value}")

        if step.gpus:
            args.extend(self._gpus_args(step))

        if step.command:
            command = [str(arg) for arg in step.command] if isinstance(step.command, list) else [step.command]
            args.append("--")
            args.extend(command)

        return args

    def _gpus_args(self, step: Step) -> list[str]:
        """Build the --gpus argument for Slurm."""
        if isinstance(step.gpus, list):
            # If given as a list, pass these args to srun as-is.
            return step.gpus
        elif step.gpus is True:
            # The simplest request, ask for one GPU.
            return ["--gpus-per-node=1"]
        else:
            # Ask for eg a specific GPU.
            return [f"--gpus-per-node={step.gpus}"]

import logging
from typing import Union, Any
from pathlib import Path
from os import getuid, getgid
from grp import getgrnam

import docker
from docker.types import DeviceRequest
from docker.errors import DockerException, APIError

from proceed.model import Step
from proceed.runner_protocol import apply_step_X11


def resolve_user(user: str) -> str:
    """Figure out user and group to run as: by name on host or container, or integer ids."""
    if user is None:
        return None

    if user.startswith("self"):
        uid = getuid()
        parts = user.split(":")
        if len(parts) > 1:
            group = parts[1]
            try:
                group_info = getgrnam(group)
                gid = group_info.gr_gid
            except Exception:
                gid = group
        else:
            gid = getgid()
        return f"{uid}:{gid}"

    return user


def normalize_volumes(
    volumes: dict[str, Union[str, dict[str, str]]],
    default_mode: str = "rw"
) -> dict[str, dict[str, str]]:
    """Convert string paths to full dict form and make relative paths absolute."""
    normalized = {}
    for host_path, volume in volumes.items():
        host_absolute = Path(host_path).absolute().as_posix()
        if isinstance(volume, str):
            bind_absolute = Path(volume).absolute().as_posix()
            normalized[host_absolute] = {"bind": bind_absolute, "mode": default_mode}
        else:
            bind_absolute = Path(volume["bind"]).absolute().as_posix()
            volume["bind"] = bind_absolute
            normalized[host_absolute] = volume
    return normalized


class DockerRunner:
    """Execute pipeline steps via Docker Engine."""

    def __init__(self, client_kwargs: dict[str, Any] = {}, max_attempts: int = 3):
        self.client_kwargs = client_kwargs
        self.max_attempts = max_attempts

    def run_container(
        self,
        step: Step,
        log_path: Path,
    ) -> tuple[str | None, int, str | None]:
        """Run one step as a Docker container.

        Returns (image_id, exit_code, error_message). On success error_message is None.
        """

        apply_step_X11(step)

        retried_exception = None
        attempts = 0
        while attempts < self.max_attempts:
            try:
                device_requests = []
                if step.gpus:
                    if isinstance(step.gpus, list):
                        gpu_strs = [str(gpu) for gpu in step.gpus]
                        logging.info(f"Container '{step.name}': requesting gpus: {gpu_strs}.")
                        gpu_request = DeviceRequest(
                            device_ids=gpu_strs,
                            capabilities=[["gpu"]]
                        )
                    else:
                        logging.info(f"Container '{step.name}': requesting all gpus.")
                        gpu_request = DeviceRequest(
                            count=-1,
                            capabilities=[["gpu"]]
                        )
                    device_requests.append(gpu_request)

                container_user = resolve_user(step.user)
                if container_user is None:
                    logging.info(f"Container '{step.name}': running as default user (might be root).")
                else:
                    logging.info(f"Container '{step.name}': running as user {container_user}.")

                if step.privileged:
                    logging.warning(f"Container '{step.name}' using privileged mode.  Only use this for troubleshooting!")

                client = docker.from_env(**self.client_kwargs)
                if isinstance(step.command, list):
                    command = [str(arg) for arg in step.command]
                else:
                    command = step.command

                # Docker 27+ removed mac_address from ContainerConfig; use NetworkingConfig instead.
                # NetworkingConfig is only wired through docker SDK when using the `network` kwarg
                # (not `network_mode`). Modes like "host", "none", and "container:*" don't support
                # per-endpoint MAC addresses, so fall back to network_mode for those.
                safe_network_mode = step.network_mode or ""
                should_use_network_config = (
                    step.mac_address
                    and safe_network_mode not in {"host", "none"}
                    and not safe_network_mode.startswith("container:")
                )
                if should_use_network_config:
                    network_name = step.network_mode or "bridge"
                    network_kwargs = {
                        "network": network_name,
                        "networking_config": {
                            network_name: client.api.create_endpoint_config(mac_address=step.mac_address)
                        }
                    }
                else:
                    network_kwargs = {"network_mode": step.network_mode}

                container = client.containers.run(
                    step.image,
                    command=command,
                    environment=step.environment,
                    device_requests=device_requests,
                    volumes=normalize_volumes(step.volumes),
                    working_dir=step.working_dir,
                    auto_remove=False,
                    remove=False,
                    detach=True,
                    user=container_user,
                    shm_size=step.shm_size,
                    privileged=step.privileged,
                    **network_kwargs,
                )
                logging.info(f"Container '{step.name}': waiting for process to complete.")

                step_log_stream = container.logs(stdout=True, stderr=True, stream=True)
                with open(log_path, 'w') as f:
                    for log_entry in step_log_stream:
                        log = log_entry.decode("utf-8")
                        f.write(log)
                        logging.info(f"Step '{step.name}': {log.strip()}")

                run_results = container.wait()
                exit_code = run_results['StatusCode']
                logging.info(f"Container '{step.name}': process completed with exit code {exit_code}")

                container.remove()

                return (container.image.id, exit_code, None)

            except APIError as api_error:
                if api_error.is_client_error():
                    logging.error(f"Container had a Docker client error.", exc_info=True)
                    error_message = f"APIError: {api_error.explanation}\n"
                    return (None, -1, error_message)
                else:
                    logging.error(f"Container had a Docker server error, will retry.", exc_info=True)
                    retried_exception = api_error

            except DockerException as docker_exception:
                logging.error(f"Container had a Docker error.", exc_info=True)
                error_message = f"{type(docker_exception).__name__}: {docker_exception.args}\n"
                return (None, -1, error_message)

            except Exception as unexpected_exception:
                # Other exceptions besides DockerException are unexpected!
                # But we have seen OSError here, for one.
                # Some of these seem to be transient, so we can retry them.
                logging.error(f"Container had an unexpected, non-Docker error, will retry", exc_info=True)
                retried_exception = unexpected_exception

            attempts += 1
            retry_log_message = f"Container attempts/retries at {attempts} out of {self.max_attempts}.\n"
            with open(log_path, 'a') as f:
                f.write(retry_log_message)
            logging.info(retry_log_message.strip())

        # Exhausted max_attempts.
        if isinstance(retried_exception, APIError):
            error_message = f"APIError: {retried_exception.explanation}\n"
        else:
            error_message = f"{type(retried_exception).__name__}: {retried_exception.args}\n"
        return (None, -1, error_message)

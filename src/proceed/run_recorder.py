import logging
from pathlib import Path

from proceed.config_options import ConfigOptions
from proceed.model import ExecutionRecord

class RunRecorder:
    """Keep track of the current ExecutionRecord, where and how to write it to disk."""

    def __init__(
        self,
        execution_path: Path,
        execution_record_name: str = "execution_record.yaml",
        config_options: ConfigOptions = ConfigOptions()
    ):
        self.config_options = config_options

        self.record_path = Path(execution_path, execution_record_name)
        logging.info(f"Will write execution record to: {self.record_path}")

    def write(
        self,
        execution_record: ExecutionRecord
    ):
        logging.info(f"Writing execution record to: {self.record_path}")
        with open(self.record_path, "w") as record:
            record.write(execution_record.to_yaml(
                skip_empty=self.config_options.yaml_skip_empty.value,
                dump_args=self.config_options.yaml_options.value
            ))

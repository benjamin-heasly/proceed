from dataclasses import dataclass, field
from typing import Any
from pipeline_stuff.yaml_data import YamlData


@dataclass
class Step(YamlData):
    """A computation step with required inputs, expected outputs, and container run parameters."""

    name: str = ""
    image: str = ""
    volumes: dict[str, Any] = field(default_factory=dict)
    command: list[str] = field(default_factory=list)


@dataclass
class Pipeline(YamlData):
    """Top-level container for Steps to run and other pipeline configuration."""
    version: str = "0.0.1"

    steps: list[Step] = field(default_factory=list)

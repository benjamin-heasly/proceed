from types import GenericAlias
from typing import Self
from dataclasses import asdict, fields
import inspect
import yaml


class YamlData():
    """Utility methods to convert @dataclass objects to and from YAML.

    These use class inspection and @dataclass utilities to figure out
    field names and types -- these do not write or use custom YAML tags.
    """

    def to_yaml(self) -> str:
        """Dump self to a plain YAML string without custom YAML tags."""

        self_dict = asdict(self)
        self_yaml = yaml.safe_dump(self_dict, sort_keys=False, default_flow_style=None)
        return self_yaml

    @classmethod
    def from_yaml(cls, instance_yaml) -> Self:
        """Read a class instance from a plain YAML string without custom YAML tags."""

        instance_dict = yaml.safe_load(instance_yaml)
        instance = cls.from_dict(instance_dict)
        return instance

    @classmethod
    def from_dict(cls, instance_dict) -> Self:
        """Read an instance of this YamlData class from a dictionary that has the same shape."""

        constructor_params = inspect.signature(cls).parameters
        sanitized_dict = {
            k: v for k, v in instance_dict.items() if k in constructor_params}
        instance = cls(**sanitized_dict)

        # The instance itself is now a YamlData subclass, but nested YamlData fields may still be dicts.
        instance.bless_yaml_data_fields()
        return instance

    @classmethod
    def field_is_yaml_data(cls, field):
        # Was this field declared as a YamlData subclass?
        return (isinstance(field.type, type)
                and issubclass(field.type, YamlData))

    @classmethod
    def field_is_list_of_yaml_data(cls, field):
        # Was this field declared as a generic list with a YamlData subclass for elements?
        return (isinstance(field.type, GenericAlias)
                and issubclass(field.type.__origin__, list)
                and issubclass(YamlData.generic_list_element_type(field), YamlData))

    @classmethod
    def generic_list_element_type(cls, field):
        # Assuming this field is a generic list, what was the declared element type?
        return field.type.__args__[0]

    def bless_yaml_data_fields(self):
        """Look for fields of self declared as YamlData subclasses, and convert these from dictionaries."""

        for field in fields(self):
            if YamlData.field_is_yaml_data(field):
                # Convert a scalar field from dict to YamlData subclass.
                field_value = getattr(self, field.name)
                if isinstance(field_value, dict):
                    field_instance = field.type.from_dict(field_value)
                    setattr(self, field.name, field_instance)
            elif YamlData.field_is_list_of_yaml_data(field):
                # Convert a list of dicts field to list of YamlData subclass.
                field_value = getattr(self, field.name)
                if isinstance(field_value, list):
                    element_type = YamlData.generic_list_element_type(field)
                    raw_list = getattr(self, field.name)
                    blessed_list = [element_type.from_dict(
                        element) for element in raw_list if isinstance(element, dict)]
                    setattr(self, field.name, blessed_list)

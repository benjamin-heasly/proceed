from typing import List, Self
from dataclasses import asdict, dataclass, field, fields
import inspect
import yaml


class YamlData():
    def to_yaml(self) -> str:
        self_dict = asdict(self)
        self_yaml = yaml.safe_dump(self_dict, sort_keys=False)
        return self_yaml
    
    @classmethod
    def from_yaml(cls, instance_yaml) -> Self:
        instance_dict = yaml.safe_load(instance_yaml)
        instance = cls.from_dict(instance_dict)
        return instance

    @classmethod
    def from_dict(cls, instance_dict) -> Self:
        constructor_params = inspect.signature(cls).parameters
        sanitized_dict = { k: v for k, v in instance_dict.items() if k in constructor_params }
        instance = cls(**sanitized_dict)

        # The instance itself is now a YamlData subclass, but nested YamlData fields may still be dicts.
        instance.bless_yaml_data_fields()
        return instance

    def bless_yaml_data_fields(self):
        for field in fields(self):
            if isinstance(field.type, type) and issubclass(field.type, YamlData):
                # This field was declared as a YamlData subclass.
                field_value = getattr(self, field.name)
                if isinstance(field_value, dict):
                    # However, the current field value is a dictionary.
                    # "Bless" the dict into an instance of the declared YamlData subclass.
                    field_instance = field.type.from_dict(field_value)
                    setattr(self, field.name, field_instance)


@dataclass
class Thing(YamlData):
    a_string: str = "food"
    an_int: int = 999
    a_list_of_float: List[float] = field(default_factory=list)


@dataclass
class Slink(YamlData):
    a_string: str = "chiun"
    a_thing: Thing = field(default_factory=Thing)


@dataclass
class Bingo(YamlData):
    a_thing: Thing
    another_thing: Thing
    a_slink: Slink


def test_to_from_yaml():
    thing_spec = """
    a_string: rootf
    an_int: 888
    some_garbage: 'dododo'
    """
    print(thing_spec)

    thing_1 = Thing.from_yaml(thing_spec)
    print(thing_1)

    thing_spec_2 = thing_1.to_yaml()
    print(thing_spec_2)

    thing_2 = Thing.from_yaml(thing_spec_2)
    print(thing_2)

    assert thing_1 == thing_2

    bingo_1 = Bingo(a_thing=thing_1, another_thing=thing_2, a_slink=Slink())
    print(bingo_1)

    bingo_spec = bingo_1.to_yaml()
    print(bingo_spec)

    bingo_2 = Bingo.from_yaml(bingo_spec)
    print(bingo_2)

    assert bingo_1 == bingo_2


if __name__ == '__main__':
    test_to_from_yaml()

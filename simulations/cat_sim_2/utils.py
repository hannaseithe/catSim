from dataclasses import fields, is_dataclass


def validate_dict(data:dict, cls:type) -> None:
    if not is_dataclass(cls):
        raise TypeError(f"Invalid Object: The dict cannot be validated against the object {cls.__name__} as it is not of type dataclass")
    if not isinstance(data, dict):
        raise TypeError(f"Invalid Type: {cls.__name__} is not of type dict")
    for attr in fields(cls):
        if attr.name not in data:
            raise ValueError(f"Invalid checkpoint: missing '{attr.name}'")
        
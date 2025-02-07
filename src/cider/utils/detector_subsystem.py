from dataclasses import dataclass


@dataclass
class DetectorSubsystem:
    name: str
    attributes: dict[str, str]
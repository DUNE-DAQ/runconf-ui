from enum import IntEnum

class SubsystemStatus(IntEnum):
    DISABLED = 0
    ENABLED = 1
    PARTIALLY_ENABLED = 2
    TOP_LEVEL_DISABLED = 3
    STATE_NOT_DEFINED = 4


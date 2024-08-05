from enum import Enum, auto

class RFMode(Enum):
    TX      = 0
    RX      = auto()


mode = RFMode.TX
print(mode.name)
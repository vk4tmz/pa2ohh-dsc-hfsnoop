
from dataclasses import dataclass
from decoder.dsc.messages.message import DscMessage

import numpy as np

@dataclass
class Event:
    pass

@dataclass  
class NewDscMessageEvent(Event):
    msg: DscMessage

@dataclass  
class LogDscInfoEvent(Event):
    txt: str

@dataclass  
class LogDscResultEvent(Event):
    txt: str    

@dataclass  
class FftUpdateEvent(Event):
    fftResult: np.ndarray
    fftAverage: np.ndarray
    bitY:int
    bitB:int
    audioBufferSize:int
    audioLo:int
    audioHi:int
    syncTmin:float
    syncTmax:float
    syncTcntminus:float
    syncTcntplus:float

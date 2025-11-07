
import io
import numpy
import pyaudio

from abc import ABCMeta, abstractmethod
from stream_utils import read_s16, S16BE
from typing import Iterable

#######################################################################
#  class AudioSource
#######################################################################

class AudioSource(metaclass=ABCMeta):
    
    sampleRate:int

    def __init__(self, sampleRate:int):
        self.sampleRate = sampleRate

    @abstractmethod
    def open(self):
        pass
    
    @abstractmethod 
    def read(self, frame_size) -> Iterable[int]:
        pass

    @abstractmethod 
    def available(self) -> int:
        pass

    @abstractmethod
    def close(self):
        pass


#######################################################################
#  class RawAudioSource
#######################################################################

PABUFFER = 4180000          # Windows=11520000 No Problem, RASPImax: 4180000 Buffer time: (PABUFFER/samplerate/2)sec (2x8 bits)
FORMAT   = pyaudio.paInt16  # Audio format 16 levels and 2 channels

class AlsaAudioSource(AudioSource):
    srcId:int
    AUDIOdevin = None
    TRACESopened = 1

    PA: pyaudio.PyAudio
    stream: pyaudio.Stream

    def __init__(self, srcId:int, sampleRate:int=44100, format=FORMAT):
        super().__init__(sampleRate)

        self.srcId = srcId

    def open(self):

        self.PA = pyaudio.PyAudio()
    
        self.stream = self.PA.open(format = FORMAT,
                channels = self.TRACESopened, 
                rate = self.sampleRate, 
                input = True,
                output = False,
                frames_per_buffer = PABUFFER,
                input_device_index = self.srcId)
        
    
    def read(self, buffervalue) -> Iterable[int]:
        signals = self.stream.read(buffervalue)          # Read samples from the buffer
        # Conversion audio samples to values -32762 to +32767 (ones complement) and add to AUDIOsignal1
        return numpy.frombuffer(signals, numpy.int16)

    def available(self) -> int:
        return self.stream.get_read_available()

    def close(self):
        try:
            self.stream.stop_stream()
        except:
            pass
        try:
            self.stream.close()
        except:
            pass
        try:
            self.PA.terminate()
        except:
            pass

#######################################################################
#  class RawAudioSource
#######################################################################

class RawAudioSource(AudioSource):
    src: io.TextIOWrapper

    def __init__(self, src: io.TextIOWrapper, endianness=S16BE, sampleRate:int=44100):
        super().__init__(sampleRate)
        self.src = src
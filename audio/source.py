
import io
import numpy
import numpy.typing as npt

import pyaudio
import select

from abc import ABCMeta, abstractmethod
from typing import Iterable, BinaryIO

#######################################################################
#  class AudioSource
#######################################################################

class AudioSource(metaclass=ABCMeta):
    
    sampleRate: int
    numChannels: int 
    chunkSize: int

    def __init__(self, sampleRate:int, numChannels:int=1):
        self.sampleRate = sampleRate
        self.numChannels = numChannels
        self.chunkSize = int(self.sampleRate / 10)

    @abstractmethod
    def open(self):
        pass
    
    @abstractmethod 
    def read(self, frame_size) -> npt.NDArray[numpy.int16]:
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

FORMAT   = pyaudio.paInt16  # Audio format 16 levels and 2 channels

class AlsaAudioSource(AudioSource):
    srcId:int
    AUDIOdevin = None

    PA: pyaudio.PyAudio
    stream: pyaudio.Stream

    def __init__(self, srcId:int, sampleRate:int=44100, format=FORMAT, numChannels:int=1):
        super().__init__(sampleRate, numChannels)

        self.srcId = srcId

    def open(self):

        self.PA = pyaudio.PyAudio()
    
        self.stream = self.PA.open(format = FORMAT,
                channels = self.numChannels, 
                rate = self.sampleRate, 
                input = True,
                output = False,
                # Determine the size of frames which will be available for reading:
                frames_per_buffer = self.chunkSize,
                input_device_index = self.srcId)
        
    
    def read(self, buffervalue) -> npt.NDArray[numpy.int16]:
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
    src: BinaryIO
    dtype:str
    readTimeout:float = 1.0

    
    def __init__(self, src: BinaryIO, dtype:str='int16', sampleRate:int=44100, numChannels:int=1):
        super().__init__(sampleRate, numChannels)
        self.src = src
        self.dtype = dtype

    def open(self):
        pass
    
    def read(self, frame_size) -> npt.NDArray[numpy.int16]:
        raw_data = None

        if select.select([self.src,],[],[],self.readTimeout)[0]:
            raw_data = self.src.read(frame_size * numpy.dtype(self.dtype).itemsize * self.numChannels)

        if not raw_data:
            return numpy.empty(0, dtype=self.dtype)

        # Convert raw bytes to a NumPy array with the correct data type
        return numpy.frombuffer(raw_data, dtype=self.dtype)


    def available(self) -> int:
        return self.chunkSize

    def close(self):
        # leave up to originator to close the stream incase being used else where.
        pass

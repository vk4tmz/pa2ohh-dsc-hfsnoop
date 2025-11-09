# DSCHFsnoop-v02c.py (16-03-2024)
# Reception of Digital Selective Calling on HF frequencies
# Made by Onno Hoekstra (pa2ohh)

# External modules: pyaudio

import argparse
import math
import sys
import time
import pyaudio
import shutil

from tkinter import *
from tkinter import messagebox
from tkinter import filedialog
from tkinter import simpledialog
from tkinter import font

import numpy

from audio import source
from DSCConfig import DscConfig
from typing import Optional


dscCfg: DscConfig

APPTitle = "MF-HF-DSC Decoder"
HLINE = "===================================" # Message separation line

############################################################################################################################################
# Initialisation of global variables required in various routines (MODIFY THEM ONLY IF NECESSARY!)
SYNCTfactor = 0.02          # Correction factor for time synchronisation
SYNCTfactorLocked = 0.01    # Correction factor for time synchronisation if phasing found
SYNCFfactor = 0.03          # Average factor for frequency synchronisation curve average
FFTwindow = False           # [DEFAULT=False] FFTwindow applied if True
ZEROpadding = 4             # [DEFAULT=4] Zero padding for extra FFT points

############################################################################################################################################
# Initialisation of OTHER global variables (DO NOT MODIFY THEM!)
DEBUG = 0                   # Print DEBUG info. 0=off; 1=level1; 2=level2. Activate with "Test Mode" button
SHIFTfrequency = 170        # 170 for MF - HF
BITrate = 100.0             # Bitrate 100 for MF - HF
AUTOscroll = True           # Auto scroll text boxes to last messages
FileDate = ""               # Date of the file names
FileDay = ""                # The current Day
FileCopy = False            # True when File has to be copied
LOWsearchf = 300            # Lowest frequency 
HIGHsearchf = 3000          # Highest frequency
FLAGmsgtest = False         # If True then it is a test message!
FLAGmsgspecial = False      # If True then it is a special message
FREQext = 0                 # Extra Offset for extended frequency with 10 Hz resolution
AUDIOsrc: Optional[source.AudioSource] = None
AUDIOsignal1 = []           # Audio trace channel 1
AUDIObuffer = 0             # Audio buffer size
RUNstatus = 0               # 0 stopped, 1 start, 2 running, 3 stop now, 4 stop and restart
BitOld = "Y"                # The previous bit
BitNew = "B"                # The new bit 
strYBY = ""                 # the YBY string from the YBY decoding process
DSCMSG = ""                 # The readable DSC message text that has to be printed and saved
MSGdata = []                # The message data
EXPMSGdata = []             # Extension message data
FTPfiles = []               # The list with FTPfiles to be uploaded
MSG = 0                     # Start of message position in strYBY
MSGstatus = 0               # 0=Search Phasing;
                            # 1=Phasing found, Decode Data;
                            # 2=Decode data to Message;
                            # 3=Error in Message decoding, set MSGstatus=0 in next Phasing search
FFTresult = []              # FFT result
FFTaverage = []             # FFT average for frequency synchronisation
FFTlength = 0               # The length of the FFT array including Zero padding
STARTsample = 0             # Start sample in the FFTresult
STOPsample = 0              # Stop sample in the FFTresult
SHIFTsamples = 0            # The 170 Hz shift in FFTsamples
SYNCTcor = 0                # Correction for time synchronisation in samples
SYNCTmin = 1.0              # Minimum correction value RESET TO +1.0                       
SYNCTmax = -1.0             # Maximum correction value RESET TO -1.0
SYNCTcntplus = 0            # Number of plus counts time synchronization
SYNCTcntminus = 0           # Number of minus counts time synchronization
SYNCTVold1 = 0.0            # The old value1
SYNCTVold2 = 0.0            # The old value2
TC1command = 0              # TC1command saved in this variable
BitY = 0                    # Y is low tone sample in FFT array
BitB = 0                    # B is high tone sample in FFT array
BitStep = 0.0               # The audio samples of one Bit
BitStepFrac = 0.0           # Fractional part in calculation

COASTmmsi = []              # MMSI in Coast data base
COASTname = []
COASTlat = []
COASTlon = []
COASTlatd = []              # Decimal latitude
COASTlond = []              # Decimal longitude
COASTindex = -1             # The match index, but -1 if no match

SHIPmmsi = []               # MMSI in Ship data base 
SHIPinfo = []
SHIPindex = -1              # The match index, but -1 if no match

POSmmsi = ""                # MMSI for possible transmitted SHIP position
POSlat = ""                 # LAT for transmitted SHIP position
POSlon = ""                 # LON for transmitted SHIP position


############################################################################################################################################

# ================================== Widget routines ========================================== 

# ... Button Start ...
def Bstart():
    global RUNstatus
    global AUDIOsignal1
   
    if (RUNstatus == 0):
        RUNstatus = 1
        AUDIOsignal1 = []
        text1.delete(1.0, END)  # Delete Info screen
        Initialize()
    else:
        if (RUNstatus == 1):
            RUNstatus = 0
        if (RUNstatus == 2 or RUNstatus == 4):
            RUNstatus = 3

    Buttontext()            # Set colors and text of buttons


# ... Button Sample rate ...
def Bsrate():
    global RUNstatus

    if RUNstatus != 0:      # Only if stopped
        return

    if dscCfg.sampleRate == 44100:
        dscCfg.sampleRate = 11025
        Buttontext()        # Set colors and text of buttons
        return

    if dscCfg.sampleRate == 11025:
        dscCfg.sampleRate = 44100
        Buttontext()        # Set colors and text of buttons
        return


#... Button enable or disable Auto scroll ...
def Bscroll():
    global AUTOscroll
    if AUTOscroll == True:
        AUTOscroll = False
    else:
        AUTOscroll = True
    Buttontext()    # Set colors and text of buttons


#... Button set frequency band for Frequency synchronisation ...
def Bsyncf():

    dscCfg.freqBand = dscCfg.freqBand + 1

    if dscCfg.freqBand > 3:
        FREQband = 0
        
    Initialize()


# ... Button Test ...
def Btest():
    global DEBUG

    DEBUG = DEBUG + 1
    if DEBUG > 2:
        DEBUG = 0
        
    if DEBUG == 0:
        PrintInfo("TESTMODE OFF")
    if DEBUG == 1:
        PrintInfo("TEST INFORMATION")
    if DEBUG > 1:
        PrintInfo("TEST INFORMATION AND RAW DATA")

    Buttontext()    # Set colors and text of buttons


# ... Button Clear Info screen ...
def BCLRinfo():
    text1.delete(1.0, END)
    Buttontext()    # Set colors and text of buttons


# ... Button Clear Log screen ...
def BCLRscreen():
    text2.delete(1.0, END)
    Buttontext()    # Set colors and text of buttons

# =============== The Mainloop =====================
def MAINloop():             # The Mainloop
    global AUDIOsignal1
    global RUNstatus

    while(True):
        FINDphasing()       # Search for the phasing signal and the start of a message
        MAKEdata()          # Make the data and call the message decoders
        SELECTdecoder()     # Select and call the decoder depending on the format specifier


# ================= Select an audio device =======================
def SELECTaudiodevice():        # Select an audio device
    global AUDIOsrc

    PA = pyaudio.PyAudio()
    ndev = PA.get_device_count()

    n = 0
    ai = ""
    ao = ""
    while n < ndev:
        s = PA.get_device_info_by_index(n)
        # print n, s
        if s['maxInputChannels'] > 0:
            ai = ai + str(s['index']) + ": " + s['name'] + "\n"
        if s['maxOutputChannels'] > 0:
            ao = ao + str(s['index']) + ": " + s['name'] + "\n"
        n = n + 1
    PA.terminate()

    AUDIOsrc = None
    
    s = simpledialog.askstring("Device","Select audio INPUT device:\nPress Cancel for Windows Default\n\n" + ai + "\n\nNumber: ")
    print(f"Audio Device - s: [{s}]")
    if (s != None):             # If Cancel pressed, then None
        try:                    # Error if for example no numeric characters or OK pressed without input (s = "")
            v = int(s)            
        except:
            s = "error"

        if s != "error":
            if v < 0 or v > ndev:
                v = 0
            AUDIOsrc = source.AlsaAudioSource(v, sampleRate=dscCfg.sampleRate)
 

# ======================= Read audio from audio input ==================================
def AUDIOin():   # Read the audio from the stream and store the data into the arrays
    global DEBUG
    global AUDIOsignal1
    global AUDIOsrc
    global RUNstatus
    global AUDIObuffer
  
    if AUDIOsrc:
    
        # ... RUNstatus == 1 : Open Stream ...
        if (RUNstatus == 1):
            AUDIOsignal1 = []

            try:
                
                AUDIOsrc.open()

                RUNstatus = 2
                txt = "Audio Stream opened Sample rate: " + str(dscCfg.sampleRate) + " samples/s"
                PrintInfo(txt)         
            except Exception as e:                                         # If error in opening audio stream, show error
                RUNstatus = 0
                PrintInfo(f"Cannot open Audio Stream. {e}")
                txt = " Sample rate: " + str(dscCfg.sampleRate) + " not supported\n"
                messagebox.showerror("Cannot open Audio Stream", txt)


        # RUNstatus == 2: Reading audio data from soundcard
        if RUNstatus == 2:
            buffervalue = AUDIOsrc.available()           # Buffer reading testroutine
            if buffervalue > AUDIObuffer:                       # Set AUDIObuffer size
                AUDIObuffer = buffervalue

            try:
                if buffervalue >= 1024:                          # >1024 to avoid problems
                    data = AUDIOsrc.read(buffervalue)
                    AUDIOsignal1.extend(data)
            except Exception as e:
                RUNstatus = 4 
                print(MakeDate(), f" Audio buffer reset! {e}")
                PrintInfo(MakeDate() + " Audio buffer reset!")
    
        # ... RUNstatus == 3: Stop; RUNstatus == 4: Stop and restart ...
        if (RUNstatus == 3) or (RUNstatus == 4):
            AUDIOsrc.close()
            
            PrintInfo(MakeDate() + " Audio Stream stopped!")
            if RUNstatus == 3:
                RUNstatus = 0                                   # Status is stopped 
            if RUNstatus == 4:
                RUNstatus = 1                                   # Status is (re)start

            AUDIOsignal1 = []                                   # Clear audio buffer
        
    root.update_idletasks()
    root.update()


# ============= Initialize variables =======================
def Initialize():
    global STARTsample
    global STOPsample
    global FFTlength
    global ZEROpadding
    global LOWsearchf
    global HIGHsearchf
    global SHIFTfrequency
    global SHIFTsamples
    global BitY
    global BitB
    global BitStep

    if dscCfg.freqBand == 0:
        LOWsearchf = 400
        HIGHsearchf = 2400

    if dscCfg.freqBand == 1:
        LOWsearchf = 1000
        HIGHsearchf = 2000

    if dscCfg.freqBand == 2:
        LOWsearchf = 1200
        HIGHsearchf = 1800

    if dscCfg.freqBand == 3:
        LOWsearchf = 1400
        HIGHsearchf = 2000

    BitStep =  dscCfg.sampleRate / BITrate
    FFTlength = 2**int(math.log2(BitStep * ZEROpadding) + 0.5)
    
    STARTsample = int(float(LOWsearchf) / (dscCfg.sampleRate / (FFTlength - 1)) + 0.5)
    STOPsample = int(float(HIGHsearchf) / (dscCfg.sampleRate / (FFTlength - 1)) + 0.5)
    SHIFTsamples = int(float(SHIFTfrequency) / (dscCfg.sampleRate / (FFTlength - 1)) + 0.5)

    BitY = int(((LOWsearchf + HIGHsearchf - SHIFTfrequency) / 2) / (dscCfg.sampleRate / (FFTlength - 1)) - STARTsample + 0.5)
    BitB = BitY + SHIFTsamples

    Buttontext()    # Set colors and text of buttons

    
# ============= Do an FFT =======================
def DoFFT(FROMsample, Length):                              # Fast Fourier transformation and others like noise blanker and level for audio meter and time markers
    global AUDIOsignal1
    global FFTresult
    global FFTwindow
    global FFTlength
    global STARTsample
    global STOPsample
    global SMPfft

    # Correction for Bandwidth of FFT window as samples left and right are suppressed by the window
    if FFTwindow == True:
        CF = 2.5                                            # Correction factor for Bandwidth of FFT window
        FROMsample = int(FROMsample - (Length * (CF - 1) / 2) + 0.5)
        Length = int(Length * CF + 0.5)
        
    while len(AUDIOsignal1) <= (FROMsample + Length + 1):   # If buffer too small, call the audio read routine
        time.sleep(0.02)                                    # Reduces processing power in loop
        AUDIOin()

    FFTsignal = AUDIOsignal1[FROMsample:FROMsample+Length]  # Take the Length samples from the stream

    # Convert list to numpy array REX for faster Numpy calculations
    REX = numpy.array(FFTsignal)                            # Make an array of the list

    # Do the FFT window function if FFTwindow == True
    if FFTwindow == True:
        W = numpy.kaiser(len(FFTsignal),8)                  # The Kaiser window with B=8 shape
        REX = REX * W                         

    # FFT with numpy 
    FFTresult = numpy.fft.fft(REX, n=FFTlength)             # Do FFT+zeropadding till n=FFTlength with NUMPY
                                                            # FFTresult = Real + Imaginary part
    FFTresult = FFTresult[STARTsample:STOPsample]           # Delete the unused samples
    FFTresult = numpy.absolute(FFTresult)                   # Make absolute SQR(REX*REX + IMX*IMX) for VOLTAGE!


# ============= Time synchronisation =======================
def SyncTime():
    global DEBUG
    global MSGstatus
    global SYNCTcor
    global SYNCTmin
    global SYNCTmax
    global SYNCTcntplus
    global SYNCTcntminus
    global SYNCTfactor
    global SYNCTfactorLocked
    global SYNCTVold1
    global SYNCTVold2 
    global BitY
    global BitB
    global BitNew
    global BitOld
    global BitStep
    global FFTresult
    global FFTaverage

    if MSGstatus == 0:                  # Not locked, do a FFT with start halfway bitstep
        SF = SYNCTfactor
        EXTRA = 1.0                     # NO extra long FFT array
    else:                               # Locked
        SF = SYNCTfactorLocked
        EXTRA = 1.5                     # A little experimental extra length when locked

    Length = int(EXTRA * BitStep + 0.5)
    Start = int(5 * BitStep - EXTRA * BitStep / 2)
    DoFFT(Start, Length)                # Do a FFT start halfway both bits

    VB = FFTresult[BitB]
    VY = FFTresult[BitY]

    if BitNew == "Y":
        V1 = VB + SYNCTVold1
        V2 = VY + SYNCTVold2
        SYNCTVold1 = VB
        SYNCTVold2 = VY
    else: # if "B"
        V1 = VY + SYNCTVold1
        V2 = VB + SYNCTVold2
        SYNCTVold1 = VY
        SYNCTVold2 = VB

    SYNCTcor = int(SF * BitStep + 0.5)
    if V1 < V2:                         # Zero crossing has to be correcter later instead of earlier
        SYNCTcor = -1 * SYNCTcor

    if SYNCTcor >= 0:                   # Count the plus and minus corrections for the display
        SYNCTcntplus = SYNCTcntplus + 1
    else:
        SYNCTcntminus = SYNCTcntminus + 1
        
    try:
        V = (VB - VY) / (VB + VY)
    except:
        V = 0,0         # Solve division by zero errors

    if V > SYNCTmax:    # For the display, orange sync line
        SYNCTmax = V
    if V < SYNCTmin:
        SYNCTmin = V


# ============= Frequency synchronisation =======================
def SyncFreq():
    global MSGstatus
    global FFTresult
    global FFTaverage
    global SYNCFfactor
    global BitY
    global BitB
    global SHIFTsamples

    if len(FFTaverage) != len(FFTresult):
        FFTaverage = FFTresult
        return

    FFTaverage = (1 - SYNCFfactor) * numpy.maximum(FFTresult, FFTaverage)   # The peak, fast attack, slow decay
   
    # FFTaverage = FFTaverage + SYNCFfactor * (FFTresult - FFTaverage)       # Average not used, fast attack is better

    if MSGstatus != 0:                                      # Only continue if MSGstatus == 0 (find phasing)
        return
 
    B = numpy.argmax(FFTaverage)                            # Find the sample number with the maximum

    if B < SHIFTsamples:
        BitY = B
        BitB = B + SHIFTsamples
        return

    if B >= len(FFTaverage) - SHIFTsamples:
        BitB = B
        BitY = B - SHIFTsamples
        return

    if FFTaverage[B-SHIFTsamples] < FFTaverage[B+SHIFTsamples]:
        BitY = B
        BitB = B + SHIFTsamples
    else:
        BitB = B
        BitY = B - SHIFTsamples


# ============= DrawSpectrum =======================
def DrawSpectrum():
    global DEBUG
    global AUDIObuffer
    global BitY
    global BitB
    global SYNCTmin
    global SYNCTmax
    global SYNCTcntplus
    global SYNCTcntminus

    # Spectrum trace
    Tline = []
    D = 1.2 * numpy.amax(FFTaverage) / dscCfg.saY      # Find the correction for the maximum

    if D == 0:
        return
    
    L = len(FFTaverage)
    n = 0
    while n < L:
        x = dscCfg.saMargin + n * dscCfg.saX / (L - 1)
        if x > (dscCfg.saX + dscCfg.saMargin):
            x = (dscCfg.saX + dscCfg.saMargin)
        Tline.append(int(x + 0.5))

        try:
            y = FFTaverage[n] / D
            if y > dscCfg.saY:
                y = dscCfg.saY
            Tline.append(int(dscCfg.saY - y + 0.5))
        except:
            Tline.append(int(dscCfg.saY / 2))
        n = n + 1               

    # Y marker
    BYline = []
    x = int(dscCfg.saMargin + BitY * dscCfg.saX / (L - 1) + 0.5) - 1
    BYline.append(x)
    BYline.append(0)
    BYline.append(x)
    BYline.append(dscCfg.saY)

    # B marker
    BBline = []
    x = int(dscCfg.saMargin + BitB * dscCfg.saX / (L - 1) + 0.5) - 1
    BBline.append(x)
    BBline.append(0)
    BBline.append(x)
    BBline.append(dscCfg.saY)

    # Audio buffer left vertical line
    Aline = []
    x = dscCfg.saMargin / 2
    Aline.append(x)
    Aline.append(dscCfg.saY)
    Aline.append(x)
    y = dscCfg.saY * AUDIObuffer / 4 / dscCfg.sampleRate      # 2 sec = 100%! 2 bytes per sample
    if y > dscCfg.saY:
        y = dscCfg.saY
    Aline.append(int(dscCfg.saY - y + 0.5))
    AUDIObuffer = AUDIObuffer * 0.9             # 0.9 instead of zero for smoothing

    # Audio level right vertical line
    LO = numpy.amin(AUDIOsignal1)
    LO = abs(LO)
    HI = numpy.amax(AUDIOsignal1)
    if LO > HI:
        HI = LO

    Lline = []
    x = dscCfg.saMargin + dscCfg.saX + dscCfg.saMargin / 2 
    Lline.append(x)
    Lline.append(dscCfg.saY)
    Lline.append(x)

    y = dscCfg.saY * HI / 32768                        # 16 bits / 2 is 32768
    if y > dscCfg.saY:
        y = dscCfg.saY
    Lline.append(int(dscCfg.saY - y + 0.5))

    # Synchronisation level bottom
    Sline = []
    if DEBUG == 2 or MSGstatus != 0:
        x = dscCfg.saMargin + dscCfg.saX / 2 + SYNCTmin * dscCfg.saX / 2
        y = dscCfg.saY - dscCfg.saMargin / 2
        Sline.append(x)
        Sline.append(y)
        x = dscCfg.saMargin + dscCfg.saX / 2 + SYNCTmax * dscCfg.saX / 2
        Sline.append(x)
        Sline.append(y)
        SYNCTmin = +1.0     # Reset SYNTmin and SYNCTmax
        SYNCTmax = -1.0

    # Synchronisation counts bottom
    R = 30                              # The reference, can be changed to what you like
    P = SYNCTcntplus + SYNCTcntminus
    if P > R:
        SYNCTcntplus = int(SYNCTcntplus * R / P)
        SYNCTcntminus = int(SYNCTcntminus * R / P)

    SCline = []
    if DEBUG == 2 or MSGstatus != 0:
        if (SYNCTcntplus + SYNCTcntminus) >= 5:   # Only if >= than 5
            V = SYNCTcntplus / (SYNCTcntplus + SYNCTcntminus)
        else:                                   # Otherwise set to center = 0.5
            V = 0.5
        x = V * dscCfg.saX + dscCfg.saMargin
        y = dscCfg.saY - dscCfg.saMargin
        SCline.append(x-dscCfg.saMargin)
        SCline.append(y)        
        SCline.append(x+dscCfg.saMargin)
        SCline.append(y)
        
    # Marker line
    Mline = []
    x = dscCfg.saMargin + dscCfg.saX / 2
    y = dscCfg.saY - dscCfg.saMargin
    Mline.append(x)
    Mline.append(y)
    y = dscCfg.saY
    Mline.append(x)
    Mline.append(y)
   
    # Delete all items on the Spectrum display
    de = ca.find_enclosed (-100, -100, dscCfg.saX+100, dscCfg.saY+100)    
    for n in de: 
        ca.delete(n)

    ca.create_line(Tline, fill="orange")        # Write the trace
    ca.create_line(BYline, fill="red", width=2) # Write the Y marker 
    ca.create_line(BBline, fill="red", width=2) # write the B marker
    
    if AUDIObuffer / 2 < dscCfg.sampleRate:            # 1 second, 2 bytes per sample
        ca.create_line(Aline, fill="green3", width=int(dscCfg.saMargin/2))     # Write the Audio buffer line green if < 50%
    else:
        ca.create_line(Aline, fill="red", width=int(dscCfg.saMargin/2))        # Write the Audio buffer line orange if overflow

    if HI < 26214:                                                      # 80% of 32768
        ca.create_line(Lline, fill="green3", width=int(dscCfg.saMargin/2))     # Write the Audio buffer line green if < 50%
    else:
        ca.create_line(Lline, fill="red", width=int(dscCfg.saMargin/2))        # Write the Audio buffer line orange if overflow

    if Sline != []:
        ca.create_line(Sline, fill="orange", width=int(dscCfg.saMargin/2))     # Write the Synchronisation line
        ca.create_line(Mline, fill="white", width=1)                    # Write the little Marker line

    if SCline != []:
        ca.create_line(SCline, fill="yellow", width=int(dscCfg.saMargin/2))    # Write the counter Synchronisation line
        
    
# ============= Convert AUDIOsignal1[] audio data to strYBY =======================
def MakeYBY():                                  # Read the audio and make strYBY
    global RUNstatus
    global DEBUG
    global strYBY
    global AUDIOsignal1
    global BitStep
    global BitStepFrac
    global BitOld           
    global BitNew
    global BitY
    global BitB
    global SYNCTcor
    global FFTaverage

    AddYBY = 0                                  # Counts the number of YBY's that have been added
    while AddYBY < 50:                          # Add xx YBY's 
        DoFFT(int(5 * BitStep), int(BitStep))   # Do a FFT start at 5*BitStep for extra buffer

        # NIET: V = FFTresult[BitY] - FFTresult[BitB] - (Yref - Bref) / 2
        V = FFTresult[BitY] - FFTresult[BitB]
        if (V > 0):
            strYBY = strYBY + dscCfg.markSym               # Add "Y" for  1 for low tone
            BitNew = dscCfg.markSym
        else:
            strYBY = strYBY + dscCfg.spaceSym              # Add "B" for 0 for high tone
            BitNew = dscCfg.spaceSym
            
        SyncFreq()

        if BitNew != BitOld:
            SyncTime()

        BitOld = BitNew

        BitStepFrac = BitStepFrac + BitStep - int(BitStep)                          # Fractional counter
        AUDIOsignal1 = AUDIOsignal1[int(BitStep + int(BitStepFrac) + SYNCTcor):]    # Delete the samples of a bit
        BitStepFrac = BitStepFrac - int(BitStepFrac)                                # Only fractional part
        SYNCTcor = 0                                                                # Reset SYNCTcor
        AddYBY = AddYBY + 1

    DrawSpectrum()                              # Draw the spectrum every xx (50)YBs = 0.5 seconds

   
# ================== Start Decoding routines =====================================================
# ============= Find the phasing signal and the start of the message MSG =======================
def FINDphasing():          
    global DEBUG
    global strYBY
    global DSCMSG
    global MSG                              # Start of message in strYBY
    global FLAGmsgtest
    global FLAGmsgspecial
    global FREQext
    global MSGstatus
    global FFTresult
    global FFTaverage

    if MSGstatus != 0 and MSGstatus != 3:   # Exit if MSGstatus not 0 or 3 (not necessary)
        return()

    if DSCMSG != "":                        # Print the DSCMSG message if not ""
        DSCsave()
        DSCMSG = ""

    FLAGmsgtest = False                     # Reset FLAGmsgtest
    FLAGmsgspecial = False                  # Reset FLAGmsgspecial
    FREQext = 0                             # Reset FREQext offset for extended frequency resolution 10Hz

    # ... Find Phasing ...

    MinBits = 50                            # The search bits in the YBY string
    Starti = 100                            # Start to search from this pointer, so that the data before this pointer can also be read
        
    if MSGstatus == 3:                      # Start of new search, skip the old part upto the format specifier
        strYBY = strYBY[(MSG+120-Starti):]  # Ready for next search of phasing signal of 120 bits
        FFTaverage = FFTresult              # Reset FFTaverage for new search
        MSGstatus = 0                       # And set the status to search

    while len(strYBY) < (Starti+MinBits+21):   # If too short, call MakeYBY; 20 islength se. +1
        MakeYBY()
    
    se1 = TENunit(108) + TENunit(125)       # Define search string 1 for phasing
    se2 = TENunit(107) + TENunit(125)       # Define search string 2 for phasing
   
    i = Starti
    L = len(strYBY)
    while i < (L - MinBits):
        if strYBY[i:(i+20)] == se1:
            MSG = i - 70
            MSGstatus = 1
            if DEBUG > 1:
                txt = MakeDate()
                PrintInfo(txt + "SYNC1found: " + str(i))
            break

        if strYBY[i:(i+20)] == se2:
            MSG = i - 90
            MSGstatus = 1
            if DEBUG > 1:
                txt = MakeDate()
                PrintInfo(txt + "SYNC2found: " + str(i))
            break

        i = i + 1

    FileHandling()
    
    if MSGstatus == 0:
        strYBY = strYBY[(MinBits+1):]
        return()

    if DEBUG > 1:
        PrintDSCresult(HLINE)
        PrintDSCresult("\n=== DEBUG DATA message ===")
        PrintDSCresult("Message found at " + str(MSG))
  
        DATAerror = 0
        strDATA = ""
        i = 1
        while DATAerror < 5:                                    # Print data till 5 errors
            strDATA = strDATA +"(" + str(GETvalsymbol(i)) + ")"
            if i > 16:                                          # End of phasing and start of data
                if GETvalsymbol(i) < 0:
                    DATAerror = DATAerror + 1
            i = i + 1

        PrintDSCresult(strDATA)


# ============= Set the Dates for the files to be saved =======================
def SetDate():
    global FileDate
    global FileDay

    DT = time.gmtime()
    FileDate = time.strftime("%Y%m%d", DT)      # The FileDate
    if dscCfg.dayOfMonth == True:
        FileDay = time.strftime("%d", DT)       # The FileDay of the Month
    else:
        FileDay = time.strftime("%w", DT)       # The FileDay of the Week (0=Sunday)
    

# ============= FileHandling saves and copies files and set the file name date =======================
def FileHandling():
    global DEBUG
    global FileDate
    global FileDay
    global FileCopy
    global FTPfiles

    DT = time.gmtime()
    M = int(time.strftime("%M", DT))    # The minute

    if M % dscCfg.ftpTime == 0 and FileCopy == True:
        FileCopy = False

        FTPfiles = []
        FTPfiles.append(dscCfg.dirDay)         # The FileDay directory for the FTP upload

        AUDIOin()                       # Empty audio buffer
        try:
            F1 = f"{dscCfg.dscAllLog.dirname}/{FileDate}{dscCfg.dscAllLog.filename}"
            F2 = f"{dscCfg.dirDay}/{FileDay}{dscCfg.dscAllLog.filename}"
            shutil.copy(F1,F2)
            if DEBUG != 0:
                PrintInfo("Minute: " + str(M) + "  FileCopy: " + F1 + " = " + F2)
        except:
            Wfile = open(F2,'w')        # Output file
            Wfile.write(dscCfg.dscAllLog.title + "\n")
            Wfile.close()               # Close the file

        FTPfiles.append(dscCfg.dscAllLog.title)
        FTPfiles.append(f"{FileDay}{dscCfg.dscAllLog.filename}")
        
        AUDIOin()                       # Empty audio buffer
        try:
            F1 = f"{dscCfg.dscMinusTestLog.dirname}/{FileDate}{dscCfg.dscMinusTestLog.filename}"
            F2 = f"{dscCfg.dirDay}/{FileDay}{dscCfg.dscMinusTestLog.filename}"
            shutil.copy(F1,F2)
            if DEBUG != 0:
                PrintInfo("Minute: " + str(M) + "  FileCopy: " + F1 + " = " + F2)
        except:
            Wfile = open(F2,'w')        # Output file
            Wfile.write(dscCfg.dscMinusTestLog.title + "\n")
            Wfile.close()               # Close the file

        FTPfiles.append(dscCfg.dscMinusTestLog.title)
        FTPfiles.append(f"{FileDay}{dscCfg.dscMinusTestLog.filename}")
                    
        AUDIOin()                       # Empty audio buffer
        try:
            F1 = f"{dscCfg.dscSpecialMsgLog.dirname}/{FileDate}{dscCfg.dscSpecialMsgLog.filename}"
            F2 = f"{dscCfg.dirDay}/{FileDay}{dscCfg.dscSpecialMsgLog.filename}"
            shutil.copy(F1,F2)
            if DEBUG != 0:
                PrintInfo("Minute: " + str(M) + "  FileCopy: " + F1 + " = " + F2)
        except:
            Wfile = open(F2,'w')        # Output file
            Wfile.write(dscCfg.dscSpecialMsgLog.title + "\n")
            Wfile.close()               # Close the file
            
        FTPfiles.append(dscCfg.dscSpecialMsgLog.title)
        FTPfiles.append(f"{FileDay}{dscCfg.dscSpecialMsgLog.filename}")

        FTPupload()

    if M % dscCfg.ftpTime != 0:
        FileCopy = True

    SetDate()


# ============= Saves files to be uploaded by FTP =======================
def FTPupload():
    global FTPfiles

    name = dscCfg.ftpFilename
    Wfile = open(name,'w')          # Open the file with the files to be uploaded

    n = 0
    while n < len(FTPfiles):        # Save the FTP file names
        filename = FTPfiles[n]
        Wfile.write(filename + "\n")
        n = n + 1

    Wfile.close()                   # Close the file
    if DEBUG != 0:
        txt = MakeDate()
        PrintInfo(txt + "FTP files stored in: " + name)

       
# ============= MAKEdata, set the data into MSGdata[]=======================
def MAKEdata():
    global DEBUG
    global strYBY
    global MSGdata
    global EXPMSGdata
    global MSG              # Start of message in strYBY
    global MSGstatus

    if MSGstatus != 1:      # Exit if MSGstatus not 1
        return()
   
    # ... Check if the double transmission of the format specifier is identical ...
    FS1 = -1                # The 1st format specifier
    FS2 = -1                # The 2nd format specifier

    FS1 = GETvalsymbol(13)
    if FS1 < 100:           # If incorrect error check bits (below -1) or not valid (below 100)
        FS1 = GETvalsymbol(18)

    FS2 = GETvalsymbol(15)
    if FS2 < 100:           # If incorrect error check bits (below -1) or not valid (below 100)
        FS2 = GETvalsymbol(20)
    
    if FS1 != FS2:
        MSGstatus = 3       # Initialize next search as both Format specifiers have to be identical
        if DEBUG != 0:
            txt = MakeDate()
            PrintInfo(txt + "Format specifiers not identical")
        return()

    # ... Make the message data and store in MSGdata ...
    Vprevious = -1
    L3Berror = False                    # True if the initial and retransmission do have a wrong 3 bits error check value
    MSGdata = []                        # Clear the data
    MSGdata.append(FS1)                 # Append the format specifier
    i = 17                              # The message starts at position 17
    while(1):                           # Loop until a break occurs
        V = GETvalsymbol(i)
        if V < 0:
            V = GETvalsymbol(i+5)       # If 3 bits error check value incorrect, take the RTX signal 5 symbols later
        if V >= 0:
            MSGdata.append(V)           # If the value has a correct CRC value, add it to the data
        else:
            L3Berror = True             # Both the initial and retransmission do have the wrong 3 bits error check value
            break
        if Vprevious == 117:            # EOS sign for Acknowledgement required, end of message
            break
        if Vprevious == 122:            # EOS sign for Acknowledgement given, end of message
            break
        if Vprevious == 127:            # EOS sign for Non acknowledgements, end of message
            break
        Vprevious = V                   # Store previous value
        
        i = i + 2

    STARTEXPMSG = i + 6                 # The possible start of the extension message

    if L3Berror == True:
        if DEBUG != 0:
            txt = MakeDate()
            PrintInfo(txt + "Error Character Check 3 last bits (2x)")
        MSGstatus = 3                   # Initialize next search as there was an error that could not be corrected
        return()

    # ... Check errors with error check character ...
    ECC = MSGrdta(0) 
    i = 1
    while i < (len(MSGdata) - 1):
        ECC = ECC ^ MSGrdta(i)
        i = i + 1
    if MSGrdta(len(MSGdata)-1) != ECC:  # The last value in the array MSGdata is the Error check symbol
        if DEBUG != 0:
            txt = MakeDate()
            PrintInfo(txt + "Data does not match with Error Check Character")
        MSGstatus = 3                   # Initialize next search as there was an error in the error check
        return()

    MSGstatus = 2                       # Status for decoding the data in MSGdata to a message
 
    # ... Search for extension message ...
    V = GETvalsymbol(STARTEXPMSG)

    NOEXPmessage = False                # True if no expansion message 
    
    if V < 100 or V > 106:              # Then no expansion message
        NOEXPmessage = True
        EXPMSGdata = []                 # Clear the EXPMSGdata[] array
        return()

    # ... Start to fill the EXPMSGdata ....
    Vprevious = -1
    EXPMSGdata = []                     # Clear the EXPMSGdata[] array
    L3Berror = False                    # True if the initial and retransmission do have a wrong 3 bits error check value
    i = STARTEXPMSG                     # The possible extension message starts at this position
    while(1):                           # Loop until a break occurs
        V = GETvalsymbol(i)
            
        if V < 0:
            V = GETvalsymbol(i+5)       # If 3 bits error check value incorrect, take the RTX signal 5 symbols later
           
        if V >= 0:
            EXPMSGdata.append(V)        # If the value has a correct CRC value, add it to the data
        else:
            L3Berror = True             # Both the initial and retransmission do have the wrong 3 bits error check value
            break

        if Vprevious == 117:            # EOS sign for Acknowledgement required, end of message
            break
        if Vprevious == 122:            # EOS sign for Acknowledgement given, end of message
            break
        if Vprevious == 127:            # EOS sign for Non acknowledgements, end of message
            break
        Vprevious = V                   # Store previous value
        
        i = i + 2
    
    if L3Berror == True:
        if DEBUG != 0:
            txt = MakeDate()
            PrintInfo(txt + "Error expansion msg, Error Character Check 3 last bits (2x)")
        EXPMSGdata = []                 # Clear the EXPMSGdata
        return()

    # ... Check errors with error check character ...
    ECC = EXPMSGrdta(0) 
    i = 1
    while i < (len(EXPMSGdata) - 1):
        ECC = ECC ^ EXPMSGrdta(i)
        i = i + 1
    if EXPMSGrdta(len(EXPMSGdata)-1) != ECC:  # The last value in the array EXPMSGdata is the Error check symbol
        if DEBUG != 0:
            txt = MakeDate()
            PrintInfo(txt + "Data expansion msg does not match with Error Check Character")
        EXPMSGdata = []
        return()
    
# ============================ Select the decoder depending on the Format specifier ==============================
def SELECTdecoder():
    global DEBUG
    global MSGdata
    global MSG          # Start of message in strYBY
    global MSGstatus
    global EXPMSGdata

    if MSGstatus != 2:                  # Exit if MSGstatus not 2
        return()
    
    if MSGrdta(0) == 102:               # Format specifier 102
        DEC102()

    if MSGrdta(0) == 112:               # Format specifier 112
        DEC112()

    if MSGrdta(0) == 114:               # Format specifier 114
        DEC114()

    if MSGrdta(0) == 116:               # Format specifier 116
        DEC116()

    if MSGrdta(0) == 120:               # Format specifier 120
        DEC120()

    if MSGrdta(0) == 123:               # Format specifier 123
        DEC123()

    if MSGstatus != 3:                  # The MSGstatus is not reset to 3, so no valid or supported format specifier
        txt = MakeDate()
        PrintInfo(txt + "Error or no supported format specifier: " + str(MSGrdta(0)))

    if len(EXPMSGdata) != 0:            # Decode the extension message
        DSCExpansion821()
        
    MSGstatus = 3                       # Continue with the next search, messages have been decoded


# ============================ Decode format specifier 102 (Selective Geographic Area) ==============================
def DEC102():
    global DEBUG
    global MSGdata
    global MSG          # Start of message in strYBY
    global MSGstatus

    PrintDSCresult(HLINE)
    txt = MakeDate()                    # The time
    PrintDSCresult(txt)
    txt = "FMS-102: Selective geographic area"
    PrintDSCresult(txt)

    DSC_ZONE(1)
    PrintDSCresult(DSC_CAT(MSGrdta(6)))
    if MSGrdta(6) == 112:                           # Category 112
        # PrintDSCresult("-------") 
        PrintDSCresult("SELF-ID: " + DSC_MMSI(7, True))
        PrintDSCresult(DSC_TC1(MSGrdta(12)))
        PrintDSCresult("DIST-ID: " + DSC_MMSI(13, False))
        PrintDSCresult(DSC_NOD(MSGrdta(18)))
        PrintDSCresult(DSC_POS(19))
        PrintDSCresult(DSC_UTC(24))
        PrintDSCresult(DSC_TC1(MSGrdta(26)))

    if MSGrdta(6) == 108 or MSGrdta(6) == 110:      # Category 108 or 110 
        # PrintDSCresult("-------") 
        PrintDSCresult("SELF-ID: " + DSC_MMSI(7, True))
        PrintDSCresult(DSC_TC1(MSGrdta(12)))
        PrintDSCresult(DSC_TC2(MSGrdta(13)))
        PrintDSCresult("FREQ-RX: " + DSC_FREQ(14))
        PrintDSCresult("FREQ-TX: " + DSC_FREQ(17+FREQext))

    PrintDSCresult(DSC_EOS(MSGrdta(len(MSGdata)-2)))
     
    MSGstatus = 3       # Continue with the next search, messages have been decoded


# ============================ Decode format specifier 112 (Disstress) ==============================
def DEC112():
    global DEBUG
    global MSGdata
    global MSG          # Start of message in strYBY
    global MSGstatus
    
    SPECIAL()           # Special message

    PrintDSCresult(HLINE)
    txt = MakeDate()    # The time
    PrintDSCresult(txt)
    txt = "FMS-112: Distress"
    PrintDSCresult(txt)
    PrintDSCresult("DIST-ID: " + DSC_MMSI(1, False))
    PrintDSCresult(DSC_NOD(MSGrdta(6)))
    PrintDSCresult(DSC_POS(7))
    PrintDSCresult(DSC_UTC(12))
    PrintDSCresult(DSC_EOS(MSGrdta(len(MSGdata)-2)))
    
    MSGstatus = 3       # Continue with the next search, messages have been decoded


# ============================ Decode format specifier 114 (Routine Group Call) ==============================
def DEC114():
    global DEBUG
    global MSGdata
    global MSG          # Start of message in strYBY
    global MSGstatus
    global FREQext
  
    PrintDSCresult(HLINE)
    txt = MakeDate()    # The time
    PrintDSCresult(txt)
    txt = "FMS-114: Routine group call"
    PrintDSCresult(txt)
    PrintDSCresult("ADRS-ID: " + DSC_MMSI(1, False))
    PrintDSCresult(DSC_CAT(MSGrdta(6)))
    # PrintDSCresult("-------")    
    PrintDSCresult("SELF-ID: " + DSC_MMSI(7, True))
    PrintDSCresult(DSC_TC1(MSGrdta(12)))
    PrintDSCresult(DSC_TC2(MSGrdta(13)))
    PrintDSCresult("FREQ-RX: " + DSC_FREQ(14))
    PrintDSCresult("FREQ-TX: " + DSC_FREQ(17+FREQext))
    PrintDSCresult(DSC_EOS(MSGrdta(len(MSGdata)-2)))
    
    MSGstatus = 3       # Continue with the next search, messages have been decoded


# ============================ Decode format specifier 116 (All Ships Call) ==============================
def DEC116():
    global DEBUG
    global MSGdata
    global MSG          # Start of message in strYBY
    global MSGstatus
    global FREQext
  
    PrintDSCresult(HLINE)
    txt = MakeDate()    # The time
    PrintDSCresult(txt)
    txt = "FMS-116: All ships call"
    PrintDSCresult(txt)

    PrintDSCresult(DSC_CAT(MSGrdta(1)))

    if MSGrdta(1) == 112:
        # PrintDSCresult("-------") 
        PrintDSCresult("SELF-ID: " + DSC_MMSI(2, True))
        PrintDSCresult(DSC_TC1(MSGrdta(7)))
        PrintDSCresult("DIST-ID: " + DSC_MMSI(8, False))
        PrintDSCresult(DSC_NOD(MSGrdta(13)))
        PrintDSCresult(DSC_POS(14))
        PrintDSCresult(DSC_UTC(19))
        PrintDSCresult(DSC_TC1(MSGrdta(21)))

    if MSGrdta(1) == 108 or MSGrdta(1) == 110:
        # PrintDSCresult("-------") 
        PrintDSCresult("SELF-ID: " + DSC_MMSI(2, True))
        PrintDSCresult(DSC_TC1(MSGrdta(7)))
        PrintDSCresult(DSC_TC2(MSGrdta(8)))
        PrintDSCresult("FREQ-RX: " + DSC_FREQ(9))
        PrintDSCresult("FREQ-TX: " + DSC_FREQ(12+FREQext))

    PrintDSCresult(DSC_EOS(MSGrdta(len(MSGdata)-2)))

    MSGstatus = 3       # Continue with the next search, messages have been decoded


# ============================ Decode format specifier 120 (Selective Individual Call) ==============================
def DEC120():
    global DEBUG
    global MSGdata
    global MSG          # Start of message in strYBY
    global FLAGmsgtest
    global FREQext
    global MSGstatus
    global MSGtest
    global DSCMSG

    PrintDSCresult(HLINE)
    txt = MakeDate()    # The time
    PrintDSCresult(txt)
    txt = "FMS-120: Selective individual call"
    PrintDSCresult(txt)

    PrintDSCresult("ADRS-ID: " + DSC_MMSI(1, False))
    PrintDSCresult(DSC_CAT(MSGrdta(6)))

    if MSGrdta(6) == 100:                       # Category 100
        # PrintDSCresult("-------") 
        PrintDSCresult("SELF-ID: " + DSC_MMSI(7, True))
        PrintDSCresult(DSC_TC1(MSGrdta(12)))
        PrintDSCresult(DSC_TC2(MSGrdta(13)))
        if MSGrdta(14) == 55:                   # Position update 1st frequency symbol=55
            PrintDSCresult(DSC_POS(15))
            SAVEpos()                           # Save the ship position
            if MSGrdta(20) < 100:               # No EOS but time
                PrintDSCresult(DSC_UTC(20))     # Add the time
        else:
            PrintDSCresult("FREQ-RX: " + DSC_FREQ(14))
            PrintDSCresult("FREQ-TX: " + DSC_FREQ(17+FREQext))

    if MSGrdta(6) == 108 or MSGrdta(6) == 110:          # Category 108 or 110
        if MSGrdta(12) == 118 and MSGrdta(14) == 126:   # Test message
            FLAGmsgtest = True                          # It is a test message and continue with decoding
        # PrintDSCresult("-------") 
        PrintDSCresult("SELF-ID: " + DSC_MMSI(7, True))
        PrintDSCresult(DSC_TC1(MSGrdta(12)))
        if MSGrdta(12) == 118 and MSGrdta(14) == 126:   # Test (118) and NO frequency or NO position information (126)
            FLAGmsgtest = True                          # It is a test message
        PrintDSCresult(DSC_TC2(MSGrdta(13)))
        if MSGrdta(14) == 55:                   # Position update 1st frequency symbol=55
            PrintDSCresult(DSC_POS(15))
            SAVEpos()                           # Save the ship position
            if MSGrdta(20) < 100:               # No EOS but time
                PrintDSCresult(DSC_UTC(20))     # Add the time
        else:
            PrintDSCresult("FREQ-RX: " + DSC_FREQ(14))
            PrintDSCresult("FREQ-TX: " + DSC_FREQ(17+FREQext))

    if MSGrdta(6) == 112:                       # Category 112 Distress
        # PrintDSCresult("-------") 
        PrintDSCresult("SELF-ID: " + DSC_MMSI(7, True))
        PrintDSCresult(DSC_TC1(MSGrdta(12)))
        PrintDSCresult("DIST-ID: " + DSC_MMSI(13, False))
        PrintDSCresult(DSC_NOD(MSGrdta(18)))
        PrintDSCresult(DSC_POS(19))
        PrintDSCresult(DSC_UTC(24))
        PrintDSCresult(DSC_TC1(MSGrdta(26)))

    PrintDSCresult(DSC_EOS(MSGrdta(len(MSGdata)-2)))
    
    MSGstatus = 3       # Continue with the next search, messages have been decoded


# ============================ Decode format specifier 123 (Selective Individual Automatic Call) ==============================
def DEC123():
    global DEBUG
    global MSGdata
    global MSG          # Start of message in strYBY
    global MSGstatus
    global FREQext
  
    PrintDSCresult(HLINE)
    txt = tMakeDate()   # The time
    PrintDSCresult(txt)
    txt = "FMS-123: Selective individual automatic call"
    PrintDSCresult(txt)

    PrintDSCresult("ADRS-ID: " + DSC_MMSI(1, False))
    PrintDSCresult(DSC_CAT(MSGrdta(6)))
    # PrintDSCresult("-------") 
    PrintDSCresult("SELF-ID: " + DSC_MMSI(7, True))    
    PrintDSCresult(DSC_TC1(MSGrdta(12)))
    PrintDSCresult(DSC_TC2(MSGrdta(13)))

    PrintDSCresult("FREQUENCY: " + DSC_FREQ(14))
    DSC_NUMBER(17 + FREQext)
    
    MSGstatus = 3       # Continue with the next search, messages have been decoded

# ============================ Decode Expansion message ==============================
def DSCExpansion821():  # Expansion message decoder ITU-R M.821
    global MSG          # Start of message in strYBY
    global HLINE        # Dashed line
    global DEBUG
    global MSGdata
    global MSG          # Start of message in strYBY
    global MSGstatus
    global EXPMSGdata

    if len(EXPMSGdata) == 0:        # Return if no message
        return()
    
    PrintDSCresult(HLINE)
    PrintDSCresult("Expansion message ITU-R M.821")
    PrintDSCresult(HLINE)

    P = 0                               # The pointer in EXPMSGdata[]
    while(1):
        if P > len(EXPMSGdata):         # Stop if the end of EXPMSGdata[] has been reached
            break

        if EXPMSGrdta(P) == 117:        # Stop if one of the 3 EOS characters
            break

        if EXPMSGrdta(P) == 122:
            break

        if EXPMSGrdta(P) == 127:
            break

        if EXPMSGrdta(P) < 100 or EXPMSGrdta(P) > 106:      # Stop if not a known expansion data specifier
            PrintDSCresult("[" + str(EXPMSGrdta(P)) + "]" + " Unknown expansion data specifier:")
            break

        TXT = ""
        if DEBUG != 0:
            TXT = "[" + str(EXPMSGrdta(P)) + "] "


        # ... 100 Enhanced position resolution ...
        if EXPMSGrdta(P) == 100:
            P = P + 1
            PrintDSCresult(TXT + "Enhanced position resolution:")
            if EXPMSGrdta(P) == 126 or EXPMSGrdta(P) == 110:
                if EXPMSGrdta(P) == 110:
                    PrintDSCresult("Enhanced position data request")
                if EXPMSGrdta(P) == 126:
                    PrintDSCresult("No enhanced position information")
                P = P + 1                               # Point to the next possible expansion data specifier
            else:
                strX = ""
                N = 0
                while N < 4:
                    if EXPMSGrdta(P+N) < 10:
                        strX = strX + "0" 
                    s = str(EXPMSGrdta(P+N))
                    strX = strX + s.strip()
                    N = N + 1
                P = P + N                               # Point to the next possible expansion data specifier

                PrintDSCresult("Latitude : " + "0." + strX[0:4])
                PrintDSCresult("Longitude: " + "0." + strX[4:9])

          
        # ... 101 Source and datum of position ...
        if EXPMSGrdta(P) == 101:
            P = P + 1
            PrintDSCresult(TXT + "Source and datum of position:")
            if EXPMSGrdta(P) == 126 or EXPMSGrdta(P) == 110:
                if EXPMSGrdta(P) == 110:
                    PrintDSCresult("Source and datum of position data request")
                if EXPMSGrdta(P) == 126:
                    PrintDSCresult("No source and datum of position information")
                P = P + 1                               # Point to the next possible expansion data specifier
            else:
                strX = ""
                N = 0
                while N < 3:
                    if EXPMSGrdta(P+N) < 10:
                        strX = strX + "0" 
                    s = str(EXPMSGrdta(P+N))
                    strX = strX + s.strip()
                    N = N + 1
                P = P + N                               # Point to the next possible expansion data specifier

                intX = int(strX[0:2])
                TXT = "[" + strX + "]" + " ERROR!! INVALID SOURCE CHARACTER"
                if intX == 0:
                    TXT = "  Current position data invalid"
                if intX == 1:
                    TXT = "  Position data from differential GPS"
                if intX == 2:
                    TXT = "  Position data from uncorrected GPS"
                if intX == 3:
                    TXT = "  Position data from differential LORAN-C"
                if intX == 4:
                    TXT = "  Position data from uncorrected LORAN-C"
                if intX == 5:
                    TXT = "  Position data from GLONASS"
                if intX == 6:
                    TXT = "  Position data from radar fix"
                if intX == 7:
                    TXT = "  Position data from Decca"
                if intX == 8:
                    TXT = "  Position data from other source"
             
                PrintDSCresult("Source : " + strX[0:2] + TXT)
                PrintDSCresult("Fix    : " + strX[2] + "." + strX[3])

                intX = int(strX[4:6])
                TXT =  "[" + strX + "]" + " ERROR!! INVALID DATE CHARACTER"
                if intX == 0:
                    TXT = "  WGS-84"
                if intX == 1:
                    TXT = "  WGS-72"
                if intX == 2:
                    TXT = "  Other"
                          
                PrintDSCresult("Date  : " + strX[4:6] + TXT)

              
        # ... 102 Vessel speed ...
        if EXPMSGrdta(P) == 102:
            P = P + 1
            PrintDSCresult(TXT + "Vessel speed:")
            if EXPMSGrdta(P) == 126 or EXPMSGrdta(P) == 110:
                if EXPMSGrdta(P) == 110:
                    PrintDSCresult("Vessel speed data request")
                if EXPMSGrdta(P) == 126:
                    PrintDSCresult("No vessel speed information")
                P = P + 1                               # Point to the next possible expansion data specifier
            else:
                strX = ""
                N = 0
                while N < 2:
                    if EXPMSGrdta(P+N) < 10:
                        strX = strX + "0" 
                    s = str(EXPMSGrdta(P+N))
                    strX = strX + s.strip()
                    N = N + 1
                P = P + N                               # Point to the next possible expansion data specifier
                
                PrintDSCresult("Speed: " + strX[0:3] + "." + strX[3] + " knots")
             
      
        # ... 103 Current course of the vessel ...
        if EXPMSGrdta(P) == 103:
            P = P + 1
            PrintDSCresult(TXT + "Current course of the vessel:")
            if EXPMSGrdta(P) == 126 or EXPMSGrdta(P) == 110:
                if EXPMSGrdta(P) == 110:
                    PrintDSCresult("Vessel course data request")
                if EXPMSGrdta(P) == 126:
                    PrintDSCresult("No vessel course information")
                P = P + 1                               # Point to the next possible expansion data specifier
            else:
                strX = ""
                N = 0
                while N < 2:
                    if EXPMSGrdta(P+N) < 10:
                        strX = strX + "0" 
                    s = str(EXPMSGrdta(P+N))
                    strX = strX + s.strip()
                    N = N + 1
                P = P + N                               # Point to the next possible expansion data specifier
                
                PrintDSCresult("Course: " + strX[0:3] + "." + strX[3] + " Degrees")

             
        # ... 104 Additional station information ...
        strExpChar = "0123456789?ABCDEFGHIJKLMNOPQRSTUVWXYZ.,-/ "
      
        if EXPMSGrdta(P) == 104:
            P = P + 1
            PrintDSCresult(TXT + "Additional station information:")
            if EXPMSGrdta(P) == 126 or EXPMSGrdta(P) == 110:
                if EXPMSGrdta(P) == 110:
                    PrintDSCresult("Additional station information data request")
                if EXPMSGrdta(P) == 126:
                    PrintDSCresult("No additional station information")
                P = P + 1                               # Point to the next possible expansion data specifier
            else:
                strX = ""
                N = 0
                while N < 99:                           # Limited to 99 characters but max 10 is allowed
                    if EXPMSGrdta(P+N) <= 41:
                        strX = strX + strExpChar[EXPMSGrdta(P+N)]
                    if EXPMSGrdta(P+N) > 41 and EXPMSGrdta(P+N) <= 99:
                        strX = strX + "?"
                    if EXPMSGrdta(P+N) > 99:            # It has to stop once...
                        break
                    N = N + 1
                P = P + N                               # Point to the next possible expansion data specifier
                
                PrintDSCresult("[" + strX + "]")

         
        # ... 105 Enhanced geographic area ...
        if EXPMSGrdta(P) == 105:
            P = P + 1
            PrintDSCresult(TXT + "Enhanced geographic area position information:")
             
            strX = ""
            N = 0
            while N < 12:
                if EXPMSGrdta(P+N) < 10:
                    strX = strX + "0" 
                s = str(EXPMSGrdta(P+N))
                strX = strX + s.strip()
                N = N + 1
            P = P + N                               # Point to the possible speed information of the Enhanced geographic area

            PrintDSCresult("Latitude ref. point : " + "0." + strX[0:4])
            PrintDSCresult("Longitude ref. point: " + "0." + strX[4:8])
            PrintDSCresult("Latitude offset     : " + "0." + strX[8:12])
            PrintDSCresult("Longitude offset    : " + "0." + strX[12:16])
            PrintDSCresult(" ")
          
            # ... Speed information enhanced geographic area data ...
            if EXPMSGrdta(P) == 126 and EXPMSGrdta(P+1) == 126:
                PrintDSCresult("No speed information")
                P = P + 2
            else:
                strX = ""
                N = 0
                while N < 2:
                    if EXPMSGrdta(P+N) < 10:
                        strX = strX + "0" 
                    s = str(EXPMSGrdta(P+N))
                    strX = strX + s.strip()
                    N = N + 1
                P = P + N                           # Point to the possible course information of the Enhanced geographic area                    

                strX = "Speed : " + strX[0:3] + "." + strX[3:4] + " knots"
                PrintDSCresult(strX)
      
            # ... Course information enhanced geographic area data ...
            if EXPMSGrdta(P+10) == 126 and EXPMSGrdta(P+11) == 126:
                PrintDSCresult("No course information")
                P = P + 2
            else:
                strX = ""
                N = 0
                while N < 2:
                    if EXPMSGrdta(P+N) < 10:
                        strX = strX + "0" 
                    s = str(EXPMSGrdta(P+N))
                    strX = strX + s.strip()
                    N = N + 1
                P = P + N                               # Point to the next possible expansion data specifier

                strX = "Course: " + strX[0:3] + "." + strX[3:4] + " Degrees"
                PrintDSCresult(strX)

        # ... 106 Number of persons on board ...
        if EXPMSGrdta(P) == 106:
            P = P + 1
            PrintDSCresult(TXT + "Number of persons on board:")
            if EXPMSGrdta(P) == 126 or EXPMSGrdta(P) == 110:
                if EXPMSGrdta(P) == 110:
                    PrintDSCresult("Number of persons on board data request")
                if EXPMSGrdta(P) == 126:
                    PrintDSCresult("No number of persons information")
                P = P + 1                               # Point to the next possible expansion data specifier
            else:
                strX = ""
                N = 0
                while N < 2:
                    if EXPMSGrdta(P+N) < 10:
                        strX = strX + "0" 
                    s = str(EXPMSGrdta(P+N))
                    strX = strX + s.strip()
                    N = N + 1
                P = P + N                               # Point to the next possible expansion data specifier

                strX = "Number of persons: " + strX
                PrintDSCresult(strX)
             
    EXPMSGdata = []         # Clear the expansion message data, otherwise it will be decoded again and again...


# =========================== Various DSC subroutines like MMSI, position, UTC etc. ================== 

# ... Decode an MMSI address ...
def DSC_MMSI(P, SelfID):
    # MMSI address
    global DEBUG
    global MSGdata
    global CC
    global COASTmmsi
    global COASTname
    global COASTlat
    global COASTlon
    global COASTindex
    global SHIPindex
    global POSmmsi
    
    CallSign = ""
    COASTindex = -1
    SHIPindex = -1
    POSmmsi = ""

    N = 0
    while N <= 4:
        if MSGrdta(P + N) < 10:
            CallSign = CallSign + "0"
        s = str(MSGrdta(P + N))
        CallSign = CallSign + s.strip()
        N = N + 1

    TXT = ""
    if DEBUG != 0:
        TXT = "[" + CallSign + "] "
        
    if CallSign[-1:] != "0":
        TXT = TXT + "ERROR! MMSI SHOULD END WITH A ZERO"
        return(TXT)

    if CallSign[0:1] != "0":                            # INDIVIDUAL
        x = int(CallSign[0:3])
        TXT = TXT + CallSign[0:9] + " INDIVIDUAL CC" + CallSign[0:3]+ " [" + dscCfg.mids[x] + "]"

        if SelfID == True:                          # Self ID station that transmits if True
            CoastDB(CallSign[0:9], dscCfg.mids[x], False)    # Might be a Coast station with a "normal" MMSI in the COAST Data base
            if COASTindex == -1:                    # No match in the COAST data base
                ShipDB(CallSign[0:9], dscCfg.mids[x], True)  # Is a "normal" ship MMSI, perhaps in the SHIP data base, Always save
                POSmmsi = CallSign[0:9]             # Callsign for possible position saving
    
    if CallSign[0:1] == "0" and CallSign[1:2] != "0":   # GROUP
        x = int(CallSign[1:4])
        TXT = TXT + CallSign[0:9] + " GROUP CC" + CallSign[1:4] + " [" + dscCfg.mids[x] + "]"
     
    if CallSign[0:1] == "0" and CallSign[1:2] == "0":   # COAST
        x = int(CallSign[2:5])
        TXT = TXT + CallSign[0:9] + " COAST CC" + CallSign[2:5] + " [" + dscCfg.mids[x] + "]"
        if SelfID == True:                          # Self ID station that transmits if True
            CoastDB(CallSign[0:9], dscCfg.mids[x], True)     # Check the COAST data base and True=ALWAYS save
            if COASTindex == -1:                    # NOT a match!
                PrintInfo("Unknown Coast station: " + CallSign[0:9])

    if COASTindex != -1:                            # A match in the COAST data base
        # TXT = TXT + "\nINFO-DB: [" + COASTmmsi[COASTindex] + " " + COASTlat[COASTindex] + " " + COASTlon[COASTindex] + " " + COASTname[COASTindex] + "]"     
        TXT = TXT + "\nINFO-DB: [" + COASTname[COASTindex] + " " + COASTlat[COASTindex] + " " + COASTlon[COASTindex] + "]"
    if SHIPindex != -1:
        # TXT = TXT + "\nINFO-DB: [" + SHIPmmsi[SHIPindex] + " " + SHIPinfo[SHIPindex] + "]"     
        TXT = TXT + "\nINFO-DB: [" + SHIPinfo[SHIPindex] + "]"
    return(TXT)
  
            
# ... Decode a frequency ...
def DSC_FREQ(P):
    global DEBUG
    global MSGdata
    global FREQext
    global TC1command
    
    intFreqErrFlag = 0

    if MSGrdta(P) == 55:
        TXT = "ERROR: POSITION NO FREQUENCY"
        return(TXT)
        
    if int(MSGrdta(P) / 10) == 4:       # Extended frequency 10 Hz resolution
        Flength = 4                     #  if "4" in accordance with R-REC-M.493-15-201901
        FREQext = FREQext + 1           # One extra bit in the message string
    else:
        Flength = 3 

    Frequency = ""
    N = 0
    while N < Flength:
        if MSGrdta(P + N) < 10:
            Frequency = Frequency + "0" 
        s = str(MSGrdta(P + N))
        Frequency = Frequency + s.strip()
        N = N + 1

    TXT = ""
    if DEBUG != 0:
        TXT = "[" + Frequency + "] "
    
    N = P
    while N < (P + Flength):
        if MSGrdta(N) != 126 and MSGrdta(N) > 99:
            intFreqErrFlag = 1
        N = N + 1

    if intFreqErrFlag == 1:
        TXT = TXT + "ERROR: SYMBOL VALUE OUTSIDE RANGE 0 - 99"
        return(TXT)

    if MSGrdta(P) == 126:
        TXT = TXT + "NONE"
        return(TXT)

    if Frequency[0] == "9":          # VHF channel!   
        if Frequency[1] != "0":
            TXT = TXT + "VHF CHANNEL ERROR! FIRST TO DIGITS SHOULD BE 90!"
            return(TXT)
     
        if int(Frequency[2]) > 2:
            TXT = TXT + "VHF CHANNEL ERROR! THIRD CHARACTER SHOULD BE LESS THAN 3!"
            return(TXT)
        
        if Frequency[2] == "0":     
            # "Frequency in accordance with RR Appendix 18 "
            pass
        
        if Frequency[2] == "1":
            # "This frequency is simplex for ship and coast station"
            pass
        
        if Frequency[2] == "2":
            # "Other frequency is simplex for ship and coast station"
            pass
        
        # ... VHF Channel ...
        TXT = TXT + Frequency[3:6] + " VHF-CHANNEL"
        return(TXT)

    if int(Frequency[0]) < 3:
        # ... Frequency ...
        TXT = TXT + str(round(float(Frequency[0:6])/10,1)) + " kHz"
        return(TXT)

    if Frequency[0] == "3":
        # ... Frequency ...
        TXT = TXT + Frequency[1:6] + " HF-CHANNEL"
        return(TXT)

    if FREQext != 0:            # Extended frequency 10 Hz resolution in accordance with R-REC-M.493-15-201901
        # ... Frequency[0] = "4" ...
        TXT = TXT + str(round(float(Frequency[1:8])/100,2)) + " kHz"
        return(TXT)

    if Frequency[0] == "8":
        # ... Frequency ...
        TXT = TXT + Frequency[0:6] +" AUTOMATED EQUIPMENT"
        return(TXT)
    
    TXT = Frequency[0:6]
    return(TXT)
 
 
# ... Decode a position ...
def DSC_POS(P):
    global DEBUG
    global MSGdata
    global POSlat
    global POSlon
    
    intPosErrFlag = 0
    POSlat = ""
    POSlon = ""

    # ... Position ...
    Position = ""
    N = 0
    while N < 5:
        if MSGrdta(P + N) < 10:
            Position = Position + "0" 
        s = str(MSGrdta(P + N))
        Position = Position + s.strip()
        N = N + 1

    TXT = ""
    if DEBUG != 0:
        TXT = "[" + Position + "] "

    TXT = TXT + "LOCATED: "
    N = P
    while N < (P + 5):
        if MSGrdta(N) != 126 and MSGrdta(N) > 99:
            intPosErrFlag = 1
        N = N + 1

    if intPosErrFlag == 1:
        TXT = TXT + "ERROR! NO VALID POSITION"
        return(TXT)

    if MSGrdta(P) == 126:
        TXT = TXT + "POSITION REQUEST"
        return(TXT)

    if Position == "9999999999":
        TXT =  TXT + "NO POSITION"
        return(TXT)
    
    # TXT = TXT + "Quadrant: " + Position[0:1] + " "
    if int(Position[0:1]) > 3:
        TXT = TXT + "ERROR! NO VALID QUADRANT"
        return(TXT)
    else:
        if int(Position[0:1]) == 0:
            # TXT = TXT + "(NE)"
            LATchar = "N"
            LONchar = "E"
        if int(Position[0:1]) == 1:
            # TXT = TXT + "(NW)"
            LATchar = "N"
            LONchar = "W"
        if int(Position[0:1]) == 2:
            # TXT = TXT + "(SE)"
            LATchar = "S"
            LONchar = "E"
        if int(Position[0:1]) == 3:
            # TXT = TXT + "(SW)"
            LATchar = "S"
            LONchar = "W"
    
    LA = Position[1:3] + "-" + Position[3:5] + LATchar
    LO = Position[5:8] + "-" + Position[8:10] + LONchar
    TXT = TXT + LA + " " + LO

    lat = int(LA[0:2]) + float(LA[3:5]) / 60
    lat = round(lat,3)
    if LATchar == "S":
        lat = -1 * lat

    lon = int(LO[0:3]) + float(LO[4:6]) / 60
    lon = round(lon,3)
    if LONchar == "W":
        lon = -1 * lon

    POSlat = str(lat)
    POSlon = str(lon)
    
    # Open Street Map link
    # https://www.openstreetmap.org/?mlat=53.2323&mlon=6.0631#map=10/53.2323/6.0631
    OSlink = "HTTPS://www.openstreetmap.org/?mlat="+str(lat)+"&mlon="+str(lon)+"#map=10/"+str(lat)+ "/"+str(lon);
    return(TXT + "\nWEBLINK: " + OSlink)


# ... SAVE a ship  position ...
def SAVEpos():
    global DIRpos
    global POSmmsi
    global POSlat
    global POSlon

    if POSmmsi == "":
        return
    if POSlat == "":
        return
    if POSlon == "":
        return
    
    dt = time.strftime("%Y%m", time.gmtime())

    AUDIOin()   # Empty audio buffer
    try:
        txt = POSmmsi + ";" + MakeDate() + ";" + "LAT" + POSlat + ";" + "LON" + POSlon
        filename = f"{dscCfg.dirPos}/{dt}.txt"
        Wfile = open(filename,'a')
        Wfile.write(txt + "\n")
        Wfile.close()
    except:
        PrintInfo(filename + " write error")

 
# ... Decode a Zone ...
def DSC_ZONE(P):
    # Zone / Area
    global DEBUG
    global MSGdata
    
    Position = ""
    N = 0
    while N <= 4:
        if MSGrdta(P + N) < 10:
            Position = Position + "0" 
        s = str(MSGrdta(P + N))
        Position = Position + s.strip()
        N = N + 1

    TXT = ""
    if DEBUG != 0:
        TXT = "[" + Position + "] "
     
    TXT = TXT + "Quadrant: " + Position[1:2] + " "
    if int(Position[0:1]) > 3:
        TXT = TXT + "ERROR! NO VALID QUADRANT"
    else:
        if int(Position[0:1]) == 0:
            TXT = TXT + "(NE)"
        if int(Position[0:1]) == 1:
            TXT = TXT + "(NW)"
        if int(Position[0:1]) == 2:
            TXT = TXT + "(SE)"
        if int(Position[0:1]) == 3:
            TXT = TXT + "(SW)"
    
    TXT = TXT + "\n"
    
    TXT = TXT + " Latitude ref. point : " + Position[1:3] + "\n"
    TXT = TXT + " Longitude ref. point: " + Position[3:6] + "\n"
    TXT = TXT + " Latitude N/S offset : " + Position[6:8] + "\n"
    TXT = TXT + " Longitude W/E offset: " + Position[8:10]
    return(TXT)
 
 
# ... Decode a time in UTC ...
def DSC_UTC(P):
    global MSGdata
    
    strUTC = ""
    N = 0
    while N <= 1:
        if MSGrdta(P + N) < 10:
            strUTC = strUTC + "0" 
        s = str(MSGrdta(P + N))
        strUTC = strUTC + s.strip()
        N = N + 1

    TXT = ""
    if DEBUG != 0:
        TXT = "[" + strUTC + "] "

    if strUTC == "8888":
        TXT = TXT + "UTCTIME: None"
    else:
        TXT = TXT + "UTCTIME: " + strUTC

    return(TXT)
 

# ... Decode a number par 8.3.3 ...
def DSC_NUMBER(P):
    global DEBUG
    global MSGdata
    
    if MSGrdta(P) != 105 and MSGrdta(P) != 106:     # Only if a number follows, 105 for odd and 106 for even
        return() 
        
    strNR = ""
    
    N = 1
    while MSGrdta(P + N) < 100:
        if MSGrdta(P + N) < 10:
            strNR = strNR + "0" 
        s = str(MSGrdta(P + N))
        strNR = strNR + s.strip()
        N = N + 1

    TXT = ""
    if DEBUG != 0:
        TXT = "[" + strNR + "] "
    
    if MSGrdta(P) == 105 and len(strNR) > 0:        # Odd numbers
        strNR = strNR[1:]                           # Skip the first zero

    TXT = TXT + "Number: " + strNR
    PrintDSCresult(TXT)


# ... Decode a category ...
def DSC_CAT(T):
    global DEBUG
    
    TXT = ""
    if DEBUG != 0:
        TXT = "[" + str(T) + "] "

    Y = "[NON EXISTING CATEGORY VALUE!]"
    if T == 100:
        Y = "[Routine]"
    if T == 103:
        Y = "[Not used anymore]"
    if T == 106:
        Y = "[Not used anymore]"
    if T == 108:
        Y = "[Safety]"
    if T == 110:
        Y = "[Urgency]"
    if T == 112:
        Y = "[Distress]"
    Y = TXT + "CAT-" + str(T) + ": " + Y[1:-1]
    return(Y)

     
# ... Decode a Nature of Distress ...
def DSC_NOD(T):
    global DEBUG
    
    TXT = ""
    if DEBUG != 0:
        TXT = "[" + str(T) + "] "

    Y = "[NON EXISTING NATURE OF DISTRESS!]"
    if T == 100:
        Y = "[Fire, Explosion]"
    if T == 101:
        Y = "[Flooding]"
    if T == 102:
        Y = "[Collision]"
    if T == 103:
        Y = "[Grounding]"
    if T == 104:
        Y = "[Listing, in danger of capsizing]"
    if T == 105:
        Y = "[Sinking]"
    if T == 106:
        Y = "[Disabled and adrift]"
    if T == 107:
        Y = "[Undesignated distress]"
    if T == 108:
        Y = "[Abandoning ship]"
    if T == 109:
        Y = "[Piracy/armed robbery attack]"
    if T == 110:
        Y = "[Man overboard]"
    if T == 112:
        Y = "[Epirb emission]"
    Y = TXT + "NOD-" + str(T) + ": " + Y[1:-1]
    return(Y)
              

# ... Decode a Telecommand 1 ...
def DSC_TC1(T):
    global DEBUG
    global TC1command
    
    TXT = ""
    if DEBUG != 0:
        TXT = "[" + str(T) + "] "

    TC1command = T      # Save TC1 in TC1command
    
    Y = "[ERROR!! NON EXISTING TELECOMMAND 1 VALUE]"
    if T == 100:
        Y = "[F3E/G3E All modes TP]"
    if T == 101:
        Y = "[F3E/G3E Duplex TP]"
    if T == 103:
        Y = "[Polling]"
    if T == 104:
        Y = "[Unable to comply]"
    if T == 105:
        Y = "[End of call (semi-automatic service only)]"
    if T == 106:
        Y = "[Data]"
    if T == 109:
        Y = "[J3E TP]"
    if T == 110:
        Y = "[Distress acknowledgement]"
    if T == 112:
        Y = "[Distress relay]"
    if T == 113:
        Y = "[F1B/J2B TTY-FEC]"
    if T == 115:
        Y = "[F1B/J2B TTY-ARQ]"
    if T == 118:
        Y = "[Test]"
    if T == 121:
        Y = "[Ship position or location registration updating]"
    if T == 126:
        Y = "[No Communication Mode information]"
    Y = TXT + "TC1-" + str(T) + ": " + Y[1:-1]
    return(Y)

     
# ... Decode a Telecommand 2 ...
def DSC_TC2(T):
    global DEBUG

    TXT = ""
    if DEBUG != 0:
        TXT = "[" + str(T) + "] "

    Y = "[ERROR!! NON EXISTING TELECOMMAND 2 VALUE]"
    if T == 100:
        Y = "[No reason]"
    if T == 101:
        Y = "[Congestion at maritime switching centre]"
    if T == 102:
        Y = "[Busy]"
    if T == 103:
        Y = "[Queue indication]"
    if T == 104:
        Y = "[Station barred]"
    if T == 105:
        Y = "[No operator available]"
    if T == 106:
        Y = "[Operator temporarily unavailable]"
    if T == 107:
        Y = "[Equipment disabled]"
    if T == 108:
        Y = "[Unable to use proposed channel]"
    if T == 109:
        Y = "[Unable to use proposed mode]"
    if T == 110:
        Y = "[Ship according to Resolution 18]"
    if T == 111:
        Y = "[Medical transports]"
    if T == 112:
        Y = "[Phone call office]"
    if T == 113:
        Y = "[Faximile/data ITU-R M.1081]"
    if T == 126:
        Y = "[No Availability information]"
    Y = TXT + "TC2-" + str(T) + ": " + Y[1:-1]
    return(Y)


# ... Decode an EOS (End Of Sequence) ...
def DSC_EOS(T):
    global DEBUG

    TXT = ""
    if DEBUG != 0:
        TXT = "[" + str(T) + "] "

    # EOS?
    Y = "ERROR!! NON EXISTING EOS VALUE"
    if T == 117:
        Y = "[Acknowledgement required]"
    if T == 122:
        Y = "[Acknowledgement given]"
    if T == 127:
        Y = "[Non acknowledgements]"
    Y = TXT + "EOS-" + str(T) + ": " + Y[1:-1]   
    return(Y)


# ======================== Various general routines ========================

# ... Convert a value to a 10 unit string code (ybyby) ...
def TENunit(Vin):
    if (Vin > 127):
         return("ERROR TENunit greater than 127") # ERROR
    
    intB = 0
    intY = 1
    Vout = ""
    
    n = 0
    while (n < 7):                     # Calculate the first 7 bits, msb(Y=1) first
        if (int(Vin) & int(intY)) != 0:
            Vout = Vout + "Y"
        else:
            Vout = Vout + "B"            
            intB = intB + 1            # Counts the number of B's (B=0)
       
        intY = intY * 2
        n = n + 1
        
    intY = 4
    n = 0
    while (n < 3):                     # Calculate the last 3 bits from intB (the number of "B"s), Msb(Y=1) first
        if (int(intB) & int(intY)) != 0:
            Vout = Vout + "Y"
        else:
            Vout = Vout + "B"            

        intY = intY / 2
        n = n + 1
    
    return(Vout)


# ... Return the value of symbol i (start at 1, only the first 7 bits are used) ...
def GETvalsymbol(i):
    global MSG                          # Start of message in strYBY
    global strYBY

    n = MSG + (i-1)*10                  # msg is start position in strYBY of message
    if n < 0:                           # If out of range of strYBY then return -1
        return(-1)
    while len(strYBY) <= n + 11:        # If strYBY is too short, call MakeYBY
        MakeYBY()

    s = strYBY[n:(n+10)]

    intB = 0
    v = 0
    if (s[0] == "Y"):
        v = v + 1
    else:
        intB = intB + 1
    if (s[1] == "Y"):
        v = v + 2
    else:
        intB = intB + 1
    if (s[2] == "Y"):
        v = v + 4
    else:
        intB = intB + 1
    if (s[3] == "Y"):
        v = v + 8
    else:
        intB = intB + 1
    if (s[4] == "Y"):
        v = v + 16
    else:
        intB = intB + 1
    if (s[5] == "Y"):
        v = v + 32
    else:
        intB = intB + 1
    if (s[6] == "Y"):
        v = v + 64
    else:
        intB = intB + 1

    Errchk = ""
    intY = 4
    n = 0
    while (n < 3):                     # Calculate the last 3 bits from intB (the number of "B"s), Msb(Y=1) first
        if ((int(intB) & int(intY)) != 0):
            Errchk = Errchk + "Y"
        else:
            Errchk = Errchk + "B"            

        intY = intY / 2
        n = n + 1

    if Errchk != s[7:]:
        v = -1 * v                      # If Error check bits wrong, return negative value

    return(v)


# ... Try to read from MSGdata[] and return that value or 127 (EOS) if not possible ...
def MSGrdta(i):
    try:
        v = MSGdata[i]
    except:
        v = 127                         # Out of range of MSGdata[], return EOS (=127)
    return(v)


# ... Try to read from EXPMSGdata[] and return that value or 127 (EOS) if not possible ...
def EXPMSGrdta(i):                      # Try to read from EXPMSGdata[]
    try:
        v = EXPMSGdata[i]
    except:
        v = 127                         # Out of range of EXPMSGdata[], return EOS (=127)
    return(v)
     

# ... If the string < s, insert spaces at the beginning ...
def Lspaces(s, k):
    while len(s) < k:
        s = " " + s
    return(s)


# ... If the string < s, add spaces at the end ...
def Rspaces(s, k):
    while len(s) < k:
        s = s + " "
    return(s)


# ... If the string < s, insert zeroes at the beginning (for making 02, 03 of 2, 3 etc.) ...
def Lzeroes(s, k):
    s = s.strip()       # remove spaces
    while len(s) < k:
        s = "0" + s
    return(s)


# ... Print a string to the Textbox 2 and add a line feed ...
def PrintResult(txt):
    global AUTOscroll
    txt = txt + "\n"
    text2.insert(END, txt)
    if AUTOscroll == True:
        text2.yview(END)


# ... Print a DSC message string to the Textbox 2 and add a line feed and save to the DSC logfile ...
def PrintDSCresult(txt):
    global AUTOscroll
    global DSCMSG
   
    DSCMSG = DSCMSG + txt + "\n"



# ... Print a string to the Info Textbox 1 and add a line feed ...
def PrintInfo(txt):
    global AUTOscroll
    txt = txt + "\n"
    text1.insert(END, txt)
    if AUTOscroll == True:
        text1.yview(END)


# ... Print a DSC message string to the Textbox 2 and add a line feed and save to the DSC logfile ...
def DSCsave():
    global AUTOscroll
    global FileDate
    global FLAGmsgtest
    global FLAGmsgspecial
    global DSCMSG
   
    text2.insert(END, DSCMSG)
    if AUTOscroll == True:
        text2.yview(END)

    filename = ""
    AUDIOin()   # Empty audio buffer
    try:
        filename = f"{dscCfg.dscAllLog.dirname}/{FileDate}{dscCfg.dscAllLog.filename}"
        Wfile = open(filename,'a')          # Output file setting
        Wfile.write(DSCMSG)
        Wfile.close()                       # Close the file
    except:
        PrintInfo(filename + " append error")

    AUDIOin()   # Empty audio buffer
    if FLAGmsgtest == False:
        try:
            filename = f"{dscCfg.dscMinusTestLog.dirname}/{FileDate}{dscCfg.dscMinusTestLog.filename}"
            Wfile = open(filename,'a')      # Output file setting
            Wfile.write(DSCMSG)
            Wfile.close()                   # Close the file
        except:
            PrintInfo(filename + " append error")
   
    AUDIOin()   # Empty audio buffer
    if FLAGmsgspecial == True:
        try:        
            filename = f"{dscCfg.dscSpecialMsgLog.dirname}/{FileDate}{dscCfg.dscSpecialMsgLog.filename}"
            Wfile = open(filename,'a')      # Output file setting
            Wfile.write(DSCMSG)
            Wfile.close()                   # Close the file
        except:
            PrintInfo(filename + " append error")


# ... Make and return a date string ...
def MakeDate():
    # d = time.strftime("[%Y%b%d-%H:%M:%S] ", time.gmtime())
    d = time.strftime("[%Y%m%d-%H:%M:%S] ", time.gmtime())
    return(d)


# ... Make button INFO red and set FLAGmsgspecial = True ...
def SPECIAL():
    global FLAGmsgspecial
    global btninfo

    FLAGmsgspecial = True
    btninfo['background'] = "red"


# ... Check Coast station data base and save the files ... 
def CoastDB(MMSI, Country, AlwaysSave):
    # Always save if AlwaysSave == True, if False only if there is a match
    global COASTindex   # Index number if a match
    global COASTmmsi    # MMSI in Coast data base
    global COASTname
    global COASTlat
    global COASTlon
    global COASTlatd    # Decimal latitude
    global COASTlond    # Decimal longitude

    n = 0
    COASTindex = -1     # No valid value
    m = int(MMSI)
    while n < len(COASTmmsi):
        mm = int(COASTmmsi[n])
        if m == mm:
            COASTindex = n
            break
        n = n + 1

    if AlwaysSave == False and COASTindex == -1: # No save if no match 
        return

    # Simple Search for an UNordered short database    
    MM = []
    n = 0
    while n < 12:
        MM.append(0)
        n = n + 1

    AUDIOin()   # Empty audio buffer
    try:
        filename = f"{dscCfg.dirCoast}/{MMSI}.txt"
        Rfile = open(filename,'r')          # Input file
        txt = Rfile.readline()              # read the first info line
        n = 0
        while n < 12:
            txt = Rfile.readline()          # read 12 month values
            MM[n] = int(txt)
            n = n + 1
        Rfile.close()
    except:
        pass 

    DT = time.gmtime()

    TheMonth = time.strftime("%m", DT)      # The FileDay of the Month
    M = int(TheMonth) - 1                   # Convert to 0 - 11
    MM[M] = MM[M] + 1

    AUDIOin()   # Empty audio buffer
    Wfile = open(filename,'w')
    txt = MMSI + "  " + MakeDate()          # Write first line
    Wfile.write(txt + "\n")

    n = 0
    while n < 12:
        txt = str(MM[n])                    # Write 12 month values
        Wfile.write(txt + "\n")
        n = n + 1

    if COASTindex == -1:
        Wfile.write(Country + "\n")
        Wfile.write("Unknown name" + "\n")
        Wfile.write("0.0" + "\n")
        Wfile.write("0.0" + "\n")
    else:
        Wfile.write(Country + "\n")
        Wfile.write(COASTname[COASTindex] + "\n")
        Wfile.write(COASTlatd[COASTindex] + "\n")
        Wfile.write(COASTlond[COASTindex] + "\n")
    Wfile.close()   


# ... Check Ship data base and save the files ... 
def ShipDB(MMSI, Country, AlwaysSave):
    # Always save if AlwaysSave == True, if False only if there is a match
    global SHIPindex
    global SHIPinfo

    n = 0
    SHIPindex = -1     # No valid value
    m = int(MMSI)
    while n < len(SHIPmmsi):
        mm =  int(SHIPmmsi[n])
        if m == mm:
            SHIPindex = n
            break
        n = n + 1
    
    if AlwaysSave == False and SHIPindex == -1: # No save if no match 
        return
    
    MM = []
    n = 0
    while n < 12:
        MM.append(0)
        n = n + 1

    AUDIOin()   # Empty audio buffer
    try:
        filename = f"{dscCfg.dirShip}/{MMSI}.txt"
        Rfile = open(filename,'r')          # Input file
        txt = Rfile.readline()              # read the first info line
        n = 0
        while n < 12:
            txt = Rfile.readline()          # read 12 month values
            MM[n] = int(txt)
            n = n + 1
        Rfile.close()
    except:
        pass 

    DT = time.gmtime()

    TheMonth = time.strftime("%m", DT)      # The FileDay of the Month
    M = int(TheMonth) - 1                   # Convert to 0 - 11
    MM[M] = MM[M] + 1

    AUDIOin()   # Empty audio buffer
    Wfile = open(filename,'w')
    txt = MMSI + "  " + MakeDate()          # Write first line
    Wfile.write(txt + "\n")

    n = 0
    while n < 12:
        txt = str(MM[n])                    # Write 12 month values
        Wfile.write(txt + "\n")
        n = n + 1

    if SHIPindex == -1:
        Wfile.write(Country + "\n")
        Wfile.write("No information" + "\n")
    else:
        Wfile.write(Country + "\n")
        Wfile.write(SHIPinfo[SHIPindex] + "\n")
    Wfile.close()   


# ... Make button text and colors ...
def Buttontext():
    global btnstart
    global btnscroll
    global btnsyncf
    global btninfo
    global btntest
    global btnmsg
    global RUNstatus
    global AUTOscroll
    global SYNCF
    global DEBUG
    global BitY
    global BitB
    global LOWsearchf
    global HIGHsearchf

    if RUNstatus == 1 or RUNstatus == 2: 
        btnstart['background'] = "green3"
        btnstart['text'] = "STOP"
    else:
        btnstart['background'] = "red"
        btnstart['text'] = "START"

    if DEBUG == 0:
        btntest['background'] = "green3"
    if DEBUG == 1:
        btntest['background'] = "orange"
    if DEBUG > 1:
        btntest['background'] = "red"

    if AUTOscroll == True:
        btnscroll['background'] = "green3"
    else:
        btnscroll['background'] = "red"

    btninfo['background'] = BTNbgcolor
    
    btnsyncf['background'] = "green3"
    txt = str(LOWsearchf) + " - " + str(HIGHsearchf)
    btnsyncf['text'] = txt

    btnsrate['background'] = "orange"
    txt = str(dscCfg.sampleRate)
    btnsrate['text'] = txt


# ... Fill the MMSI MuliPSK coast data base ...
def FillMultiPSKcoast(dbasename):
    global COASTmmsi
    global COASTname
    global COASTlatd
    global COASTlond
    global COASTlat
    global COASTlon

    COASTmmsi = []
    COASTname = []
    COASTlatd = []
    COASTlond = []
    COASTlat = []
    COASTlon = []

    try:
        filename = "./" + dbasename
        # Rfile = open(ilename,'r', encoding='utf-8', errors='ignore') # Input file
        Rfile = open(filename,'r') # Input file
    except:
        PrintInfo("No COAST database [" + filename + "]")
        return

    nopos = 0 
    line = 0  
    while(True):
        line = line + 1
        txt = Rfile.readline()          # Read the next line
        if txt == "":                   # Till empty = end
            Rfile.close()               # Close the file
            break                       # And exit the while loop

        try:
            Vmmsi = txt[0:9]
            s = int(Vmmsi)              # Check for integer number
        
            Vlat = txt[10:12] + "." + txt[13:15] + txt[16]

            Vlatd = int(txt[10:12]) + round(int(txt[13:15])/60,3)
            if txt[16] == "S":
                Vlatd = -1 * Vlatd

            Vlon = txt[18:21] + "." + txt[22:24] + txt[25]

            Vlond = int(txt[18:21]) + round(int(txt[22:24])/60,3)
            if txt[25] == "W":
                Vlond = -1 * Vlond

            if Vlatd == 0.0 and Vlond == 0.0:
                nopos = nopos + 1

            Vinfo = txt[27:-1]          # -1 to delete the LF or CR
        
            COASTmmsi.append(Vmmsi)
            COASTlat.append(Vlat)
            COASTlatd.append(str(Vlatd))            
            COASTlon.append(Vlon)
            COASTlond.append(str(Vlond))
            COASTname.append(Vinfo)
            # print("["+Vmmsi+"]["+Vlat+"]["+str(Vlatd)+"]["+Vlon+"]["+str(Vlond)+"]["+Vinfo+"]")
        except:
            PrintInfo("COAST data base error line: " + str(line))

    Rfile.close()                       # Close the file

    PrintInfo(filename + " data base inputs: " + str(len(COASTmmsi)) + " - Without position: " + str(nopos))


# ... Fill the MuliPSK ship data base ...
def FillMultiPSKship(dbasename):
    global SHIPmmsi
    global SHIPinfo

    SHIPmmsi = []
    SHIPinfo = []

    try:
        filename = "./" + dbasename
        # Rfile = open(filename,'r', encoding='utf-8', errors='ignore') # Input file
        Rfile = open(filename,'r') # Input file
    except:
        PrintInfo("No SHIP database [" + filename + "]")
        return
        
    line = 0  
    while(True):
        line = line + 1
        txt = Rfile.readline()          # Read the next line
        if txt == "":                   # Till empty = end
            Rfile.close()               # Close the file
            break                       # And exit the while loop

        try:
            Vmmsi = txt[0:9]
            s = int(Vmmsi)              # Check for integer number

            Vinfo = txt[10:-1]          # -1 to delete the LF or CR    

            SHIPmmsi.append(Vmmsi)
            SHIPinfo.append(Vinfo)
            # print("["+Vmmsi+"]["+Vinfo+"]")
        except:
            PrintInfo("SHIP data base error line: " + str(line))

    Rfile.close()                       # Close the file

    PrintInfo(filename + " data base inputs: " + str(len(SHIPmmsi)))


# ... Fill the YADD coast data base ...
def FillYADDcoast(dbasename):
    global COASTmmsi
    global COASTname
    global COASTlatd
    global COASTlond
    global COASTlat
    global COASTlon

    COASTmmsi = []
    COASTname = []
    COASTlatd = []
    COASTlond = []
    COASTlat = []
    COASTlon = []

    try:
        filename = "./" + dbasename
        Rfile = open(filename,'r', encoding='utf-8', errors='ignore') # Input file
        # Rfile = open(filename,'r') # Input file
    except:
        PrintInfo("No COAST database [" + filename + "]")
        return
                  
    line = 0
    nopos = 0 
    while(True):
        line = line + 1
        txt = Rfile.readline()          # Read the next line
        if txt == "":                   # Till empty = end
            Rfile.close()               # Close the file
            break                       # And exit the while loop

        try:
            L = txt.split(",")          # Split comma separated
            
            Vmmsi = L[0]
            s = int(Vmmsi)              # Check for integer number
        
            Vlatd = round(float(L[3]),3)
            Vlond = round(float(L[4]),3)

            if Vlatd == 0.0 and Vlond == 0.0:
                nopos = nopos + 1

            # Calculate Vlat
            if Vlatd < 0:
                C = "S"             # North
                V = -1 * Vlatd
            else:
                C = "N"             # South
                V = Vlatd
                
            s1 = str(int(V + 100))
            s1 = s1[1:]                         # Remove the "1"
            s2 = str(int(60 * (V % 1) + 0.5) + 100)
            s2 = s2[1:]                         # Remove the "1"            
            Vlat = s1 + "." + s2 + C

            # Calculate Vlon
            if Vlond < 0:
                C = "W"             # West
                V = -1 * Vlond
            else:
                C = "E"             # East
                V = Vlond

            s1 = str(int(V + 1000))
            s1 = s1[1:]                         # Remove the "1"
            s2 = str(int(60 * (V % 1) + 0.5) + 100)
            s2 = s2[1:]                         # Remove the "1"            
            Vlon = s1 + "." + s2 + C

            Vinfo = L[2]
        
            COASTmmsi.append(Vmmsi)
            COASTlat.append(Vlat)
            COASTlatd.append(str(Vlatd))            
            COASTlon.append(Vlon)
            COASTlond.append(str(Vlond))
            COASTname.append(Vinfo)
            # print("["+Vmmsi+"]["+Vlat+"]["+str(Vlatd)+"]["+Vlon+"]["+str(Vlond)+"]["+Vinfo+"]")
        except:
            PrintInfo("COAST data base error line: " + str(line))

    Rfile.close()                       # Close the file

    PrintInfo(filename + " data base inputs: " + str(len(COASTmmsi)) + " - Without position: " + str(nopos))


# ... Fill the MuliPSK ship data base ...
def FillYADDship(dbasename):
    global SHIPmmsi
    global SHIPinfo

    SHIPmmsi = []
    SHIPinfo = []

    try:
        filename = "./" + dbasename
        Rfile = open(filename,'r', encoding='utf-8', errors='ignore') # Input file
        # Rfile = open(filename,'r') # Input file
    except:
        PrintInfo("No SHIP database [" + filename + "]")
        return
        
    line = 0  
    while(True):
        line = line + 1
        txt = Rfile.readline()          # Read the next line
        if txt == "":                   # Till empty = end
            Rfile.close()               # Close the file
            break                       # And exit the while loop

        try:
            Vmmsi = txt[0:9]
            s = int(Vmmsi)              # Check for integer number

            Vinfo = txt[10:-1]          # -1 to delete the LF or CR    

            SHIPmmsi.append(Vmmsi)
            SHIPinfo.append(Vinfo)
            # print("["+Vmmsi+"]["+Vinfo+"]")
        except:
            PrintInfo("SHIP data base error line: " + str(line))
        
    Rfile.close()                       # Close the file

    PrintInfo(filename + " data base inputs: " + str(len(SHIPmmsi)))

# ================ Start Make Screen ======================================================

def initializeUI(dscCfg:DscConfig):
    global root
    global btnstart
    global btnscroll
    global btnsyncf
    global btninfo
    global btntest
    global btnmsg
    global BTNbgcolor
    global btnsrate
    global text1
    global text2
    global ca
        

    root=Tk()
    root.title(f"{APPTitle} - Monitoring Freq: [{dscCfg.freqRxHz/1000:.01f}] kHz")

    root.minsize(100, 100)

    frame1 = Frame(root, background="blue", borderwidth=5, relief=RIDGE)
    frame1.pack(side=TOP, expand=1, fill=X)

    frame1a = Frame(root, background="blue", borderwidth=5, relief=RIDGE)
    frame1a.pack(side=TOP, expand=1, fill=X)

    frame2 = Frame(root, background="black", borderwidth=5, relief=RIDGE)
    frame2.pack(side=TOP, expand=1, fill=X)

    scrollbar1 = Scrollbar(frame1)
    scrollbar1.pack(side=RIGHT, expand=NO, fill=BOTH)

    text1 = Text(frame1, height=1, width=100, yscrollcommand=scrollbar1.set)
    text1.pack(side=RIGHT, expand=1, fill=BOTH)

    ca = Canvas(frame1, width=(dscCfg.saX + 2*dscCfg.saMargin), height=dscCfg.saY, background="grey")
    ca.pack(side=LEFT)

    scrollbar1.config(command=text1.yview)

    btnstart = Button(frame1a, text="--", width=dscCfg.buttonWidth, command=Bstart)
    btnstart.pack(side=LEFT)

    btnsrate = Button(frame1a, text="--", width=dscCfg.buttonWidth, command=Bsrate)
    btnsrate.pack(side=LEFT)

    btnsyncf = Button(frame1a, text="--", width=dscCfg.buttonWidth, command=Bsyncf)
    btnsyncf.pack(side=LEFT)

    btnscroll = Button(frame1a, text="Auto Scroll", width=dscCfg.buttonWidth, command=Bscroll)
    btnscroll.pack(side=LEFT)

    btninfo = Button(frame1a, text="Clear Info", width=dscCfg.buttonWidth, command=BCLRinfo)
    btninfo.pack(side=RIGHT)

    BTNbgcolor = btninfo.cget("background")

    btnmsg = Button(frame1a, text="Clear MSGs", width=dscCfg.buttonWidth, command=BCLRscreen)
    btnmsg.pack(side=RIGHT)

    btntest = Button(frame1a, text="Test Mode", width=dscCfg.buttonWidth, command=Btest)
    btntest.pack(side=RIGHT)

    scrollbar2 = Scrollbar(frame2)
    scrollbar2.pack(side=RIGHT, expand=NO, fill=BOTH)

    text2 = Text(frame2, height=33, width=150, yscrollcommand=scrollbar2.set)
    text2.pack(side=TOP, expand=1, fill=X)

    scrollbar2.config(command=text2.yview)

    root.update()                       # Activate updated screens

    Buttontext()                        # Set colors and text of buttons

    if dscCfg.dbCoast == 1:
        FillMultiPSKcoast("MultiPSKcoast.txt")  # Load the MultiPSKcoast data base
    if dscCfg.dbCoast == 2:
        FillYADDcoast("YADDcoast.txt")          # Load the YADDcoast data base

    if dscCfg.dbShip == 1:
        FillMultiPSKship("MultiPSKship.txt")    # Load the MultiPSKship data base
    if dscCfg.dbShip == 2:
        FillYADDship("YADDship.txt")        # Load the YADDcoast data base


# ================ Main routine ================================================

def processArgs(parser):

    parser = argparse.ArgumentParser(description=APPTitle)
    parser.add_argument("freq_hz", type=int, help="Frequency (Hz) which feed is streaming from.")
    parser.add_argument("-as", "--audio-src", type=str, default="alsa", choices=["alsa","-"], help="Source for audio feed. Expected s16be format for raw / STDIN feed.")
    parser.add_argument("-sr", "--sig-rate", type=int, default=44100, choices=[11025, 22050, 44100], help="Audio sample.")
    parser.add_argument("-dd", "--data-dir", type=str, default="./data", help="Root level for data files.")
    parser.add_argument("-inv", "--invert-tones", action='store_true', help="Invert Marker(Y) / Space(B) Tones.")
    
    args = parser.parse_args()

    return args        


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=APPTitle)
    args = processArgs(parser)

    dscCfg = DscConfig(dataDir=args.data_dir,freqRxHz=args.freq_hz, sampleRate=args.sig_rate, invertTones=args.invert_tones)

    initializeUI(dscCfg)
    Initialize()                        # Set variables

    SetDate()                           # Set the Date for the file savings

    if (args.audio_src == "alsa"):
        SELECTaudiodevice()             # Select an audio device
        PrintInfo("Press START to start")
    elif (args.audio_src == "-"):
        AUDIOsrc = source.RawAudioSource(src=sys.stdin.buffer)
        # Auto Start Feed
        Bstart()

    MAINloop()                          # Start the main  loop



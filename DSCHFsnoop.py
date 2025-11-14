# DSCHFsnoop.py 
# Reception of Digital Selective Calling on HF frequencies
# Orginal Version: Onno Hoekstra (pa2ohh)
# Modernised By: Mark Rutherford (vk4tmz)

import argparse
import sys
import time
import pyaudio
import shutil

from tkinter import *
from tkinter import messagebox
from tkinter import simpledialog

from pyventus.events import EventLinker

import numpy
import queue

from audio import source
from db.DSCDatabases import DscDatabases
from DSCConfig import DscConfig
from decoder.DSCDecoder import DSCDecoder, LM_AUTO, LM_MANUAL
from decoder.DSCEvents import Event, FftUpdateEvent, NewDscMessageEvent, LogDscInfoEvent, LogDscResultEvent
from decoder.DSCMessage import DscMessage, DscSelectiveIndividualCallMsg

from utils import getTimeStamp, writeStringToFile

dscCfg: DscConfig
dscDB: DscDatabases
dscDec: DSCDecoder

AUDIOsrc: source.AudioSource

ui_msg_queue = queue.Queue()

APPTitle = "MF-HF-DSC Decoder"
HLINE = "==================================="       # Message separation line

############################################################################################################################################
# Initialisation of OTHER global variables (DO NOT MODIFY THEM!)
DEBUG = 0                   # Print DEBUG info. 0=off; 1=level1; 2=level2. Activate with "Test Mode" button
AUTOscroll = True           # Auto scroll text boxes to last messages
FileDate = ""               # Date of the file names
FileDay = ""                # The current Day
FileCopy = False            # True when File has to be copied
LOWsearchf = 300            # Lowest frequency 
HIGHsearchf = 3000          # Highest frequency
RUNstatus = 0               # 0 stopped, 1 start, 2 running, 3 stop now, 4 stop and restart
FTPfiles = []               # The list with FTPfiles to be uploaded

FFTaverage = []             # FFT average for frequency synchronisation
AUDIObuffer = 0             # Audio buffer size

############################################################################################################################################


# ================================== Widget routines ========================================== 

# ... Button Start ...
def Bstart():
    global dscDec
    global AUDIOsrc
    global RUNstatus

    if (RUNstatus == 0):
        RUNstatus = 1

        text1.delete(1.0, END)  # Delete Info screen
        
        try:
            # Start Decoder Handler
            #dscDec = DSCDecoder(audioSrc, lockMode=LM_MANUAL, centerFreq=1700)
            dscDec = DSCDecoder(AUDIOsrc, dscCfg, lockMode=LM_AUTO, tonesInverted=dscCfg.invertTones)
            dscDec.setDebugLevel(DEBUG)
            dscDec.setFreqBand(LOWsearchf, HIGHsearchf)
            dscDec.startDecoder()

            txt = "Decoding has started. Using Sample rate: " + str(dscCfg.sampleRate) + " samples/s"
            PrintInfo(txt)
            
            Initialize()
        except Exception as e:
            txt = f"Failed to start decoder. {e}"
            PrintInfo(txt)
            messagebox.showerror("Error", txt)

    else:
        if (RUNstatus == 1):
            RUNstatus = 0
            try:
                dscDec.stopDecoder()
            except Exception as e:
                txt = f"Error while attempting to stop decoder. {e}"
                PrintInfo(txt)
                messagebox.showerror("Error", txt)

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
        dscCfg.freqBand = 0

    Initialize()
    dscDec.setFreqBand(LOWsearchf, HIGHsearchf)        


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

    dscDec.setDebugLevel(DEBUG)

    Buttontext()    # Set colors and text of buttons


# ... Button Clear Info screen ...
def BCLRinfo():
    text1.delete(1.0, END)
    Buttontext()    # Set colors and text of buttons


# ... Button Clear Log screen ...
def BCLRscreen():
    text2.delete(1.0, END)
    Buttontext()    # Set colors and text of buttons

def check_queue():
    try:
        while True:
            msg = ui_msg_queue.get_nowait()  # Get message without blocking

            if isinstance(msg, FftUpdateEvent):
                DrawSpectrum(msg)
                
            elif isinstance(msg, NewDscMessageEvent):
                if (msg.msg.isSpecialMsg):
                    SPECIAL();
                
                if (isinstance(msg.msg, DscSelectiveIndividualCallMsg)):
                    SAVEpos(msg.msg)
                
                DSCsave(msg.msg)

            elif isinstance(msg, LogDscInfoEvent):
                PrintInfo(msg.txt)

            elif isinstance(msg, LogDscResultEvent):
                PrintResult(msg.txt)

            else:
                print(f"WARNING: unhandled UI event message - [{msg.__class__.__name__}]")

            root.update_idletasks() # Ensure UI updates immediately
    except queue.Empty:
        pass  # No messages in the queue

    # Common logic to run
    FileHandling()

    # Reschedule checking the queue
    root.after(100, check_queue)

# =============== The Mainloop =====================
def MAINloop():             # The Mainloop
    # Start checking the queue periodically
    root.after(100, check_queue)
    root.mainloop();

    dscDec.stopDecoder()


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
 

# ============= Initialize variables =======================
def Initialize():
    global LOWsearchf
    global HIGHsearchf
    global DEBUG

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

    Buttontext()    # Set colors and text of buttons

# ============= DrawSpectrum =======================


@EventLinker.on(FftUpdateEvent, NewDscMessageEvent, LogDscInfoEvent, LogDscResultEvent)
def handleEvents(e:Event):
    ui_msg_queue.put(e)


def DrawSpectrum(e:FftUpdateEvent):
    global DEBUG
    global AUDIObuffer

    if e.audioBufferSize > AUDIObuffer:                       # Set AUDIObuffer size
        AUDIObuffer = e.audioBufferSize

    # Spectrum trace
    Tline = []
    D = 1.2 * numpy.amax(e.fftAverage) / dscCfg.saY      # Find the correction for the maximum

    if D == 0:
        return
    
    L = len(e.fftAverage)
    n = 0
    while n < L:
        x = dscCfg.saMargin + n * dscCfg.saX / (L - 1)
        if x > (dscCfg.saX + dscCfg.saMargin):
            x = (dscCfg.saX + dscCfg.saMargin)
        Tline.append(int(x + 0.5))

        try:
            y = e.fftAverage[n] / D
            if y > dscCfg.saY:
                y = dscCfg.saY
            Tline.append(int(dscCfg.saY - y + 0.5))
        except:
            Tline.append(int(dscCfg.saY / 2))
        n = n + 1               

    # Y marker
    BYline = []
    x = int(dscCfg.saMargin + e.bitY * dscCfg.saX / (L - 1) + 0.5) - 1
    BYline.append(x)
    BYline.append(0)
    BYline.append(x)
    BYline.append(dscCfg.saY)

    # B marker
    BBline = []
    x = int(dscCfg.saMargin + e.bitB * dscCfg.saX / (L - 1) + 0.5) - 1
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
    LO = e.audioLo
    HI = e.audioHi
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
    if dscDec.dem.isLockFreq:
        x = dscCfg.saMargin + dscCfg.saX / 2 + e.syncTmin * dscCfg.saX / 2
        y = dscCfg.saY - dscCfg.saMargin / 2
        Sline.append(x)
        Sline.append(y)
        x = dscCfg.saMargin + dscCfg.saX / 2 + e.syncTmax * dscCfg.saX / 2
        Sline.append(x)
        Sline.append(y)
        

    # Synchronisation counts bottom
    R = 30                              # The reference, can be changed to what you like
    P = e.syncTcntplus + e.syncTcntminus
    if P > R:
        e.syncTcntplus = int(e.syncTcntplus * R / P)
        e.syncTcntminus = int(e.syncTcntminus * R / P)

    SCline = []
    if dscDec.dem.isLockFreq:
        if (e.syncTcntplus + e.syncTcntminus) >= 5:   # Only if >= than 5
            V = e.syncTcntplus / (e.syncTcntplus + e.syncTcntminus)
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
        txt = getTimeStamp()
        PrintInfo(txt + "FTP files stored in: " + name)

       
# ... SAVE a ship  position ...
def SAVEpos(msg:DscSelectiveIndividualCallMsg):

    if (not msg.canLogPosition):
        return

    posMmsi = msg.selfId.callsign
    posLat = msg.pos.lat
    posLon = msg.pos.lon
    
    dt = time.strftime("%Y%m", time.gmtime())
    filename = f"{dscCfg.dirPos}/{dt}.txt"
    try:
        txt = f"{posMmsi};{getTimeStamp()};LAT{posLat};LON{posLon}"
        writeStringToFile(filename, txt + "\n", append=True)
    except:
        PrintInfo(filename + " write error")


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


# ... Print a string to the Info Textbox 1 and add a line feed ...
def PrintInfo(txt):
    global AUTOscroll
    txt = txt + "\n"
    text1.insert(END, txt)
    if AUTOscroll == True:
        text1.yview(END)


# ... Print a DSC message string to the Textbox 2 and add a line feed and save to the DSC logfile ...
def DSCsave(msg:DscMessage):
    global AUTOscroll
    global FileDate
    global FLAGmsgtest
    global FLAGmsgspecial
    
    out = []    
    msg.print(out)
    DSCMSG = f"{HLINE}\n"
    DSCMSG += f"[{getTimeStamp()}\n]"
    for ln in out:
        DSCMSG += f"{ln}\n"
    
    text2.insert(END, DSCMSG)
    if AUTOscroll == True:
        text2.yview(END)

    filename = ""
    try:
        filename = f"{dscCfg.dscAllLog.dirname}/{FileDate}{dscCfg.dscAllLog.filename}"
        Wfile = open(filename,'a')          # Output file setting
        Wfile.write(DSCMSG)
        Wfile.close()                       # Close the file
    except:
        PrintInfo(filename + " append error")

    if not msg.isTestMsg:
        try:
            filename = f"{dscCfg.dscMinusTestLog.dirname}/{FileDate}{dscCfg.dscMinusTestLog.filename}"
            Wfile = open(filename,'a')      # Output file setting
            Wfile.write(DSCMSG)
            Wfile.close()                   # Close the file
        except:
            PrintInfo(filename + " append error")
   
    if msg.isSpecialMsg:
        try:        
            filename = f"{dscCfg.dscSpecialMsgLog.dirname}/{FileDate}{dscCfg.dscSpecialMsgLog.filename}"
            Wfile = open(filename,'a')      # Output file setting
            Wfile.write(DSCMSG)
            Wfile.close()                   # Close the file
        except:
            PrintInfo(filename + " append error")


# ... Make button INFO red and set FLAGmsgspecial = True ...
def SPECIAL():
    global btninfo

    btninfo['background'] = "red"


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
    global DEBUG
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

# ================ Main routine ================================================

def processArgs(parser):

    parser = argparse.ArgumentParser(description=APPTitle)
    parser.add_argument("freq_hz", type=int, help="Frequency (Hz) which feed is streaming from.")
    parser.add_argument("-as", "--audio-src", type=str, default="alsa", choices=["alsa","-"], help="Source for audio feed. Expected s16be format for raw / STDIN feed.")
    parser.add_argument("-sr", "--sig-rate", type=int, default=44100, choices=[11025, 22050, 44100], help="Audio sample.")
    parser.add_argument("-fb", "--freq-band", type=int, default=0, choices=[0,1,2,3], help="Freq bands to auto search for tones. (0 - 400-2000Hz,  1 - 1000-2000Hz,  2 - 1200-1800Hz,  3 - 1400-2000Hz")
    parser.add_argument("-dd", "--data-dir", type=str, default="./data", help="Root level for data files.")
    parser.add_argument("-inv", "--invert-tones", action='store_true', help="Invert Marker(Y) / Space(B) Tones.")
    
    args = parser.parse_args()

    return args        


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=APPTitle)
    args = processArgs(parser)

    dscCfg = DscConfig(dataDir=args.data_dir,freqRxHz=args.freq_hz, sampleRate=args.sig_rate, invertTones=args.invert_tones, freqBand=args.freq_band)
    dscDB = DscDatabases(dscCfg)

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

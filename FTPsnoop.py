# FTPsnoop-v01a.py(w) (17-06-2023)
# For uploading of the data files of XXXsnoop.py
# For Python version 3
# Made by Onno Hoekstra (pa2ohh)

# External modules: None

import os
import time
import ftplib

from time import gmtime, strftime

# ========== !!!Settings that have to be changed by the user!!! ==========================
FTPhost = "ftp.qsl.net"
FTPuser = "pa2ohh"
FTPdir = "./dsc"
FTPpassword = "password"

TXTupload = True   # Do not upload the text files if False
HTMLupload = True  # Do not upload the html files if False

# ================ Initialization of variables ===========================================
FTPFILES = "FTPuploads.txt"     # Has to be identical in the DSC decoder program!!!

DIRday = ""                     # Read from file
FTPfiles = ""                   # Read from file

# ================ CONTROL (main routine) ================================================
def CONTROL():          # Control of the whole process
    global FTPFILES

    print("FTPsnoop started")
    while(1):
        if os.path.exists(FTPFILES):
            time.sleep(60)                      # Give the DSC decoder time to finish writing the file names
            FTPupload()
            os.remove(FTPFILES)                 # Remove the file after it is used and wait for the new one
            print(FTPFILES + " removed")
        else:
            print("CHECK: " + FTPFILES + " does not exist")
            time.sleep(30)                      # Next check of the FTPFILES file exist after 30 seconds


# ================ FTP upload ================================================
def FTPupload():
    global FTPFILES
    global FTPhost
    global FTPuser
    global FTPdir
    global FTPpassword
    global DIRday
    global FTPfiles
    global TXTupload
    
    FTPfiles = ""
    DIRday = ""
   
    t = time.time()
    T =time.gmtime(t)
    txt = strftime("%H:%M:%S", T)
    print(txt + "-start FTP upload")

    FTPfiles = []                               # Array that will be filled with the file names
    
    try:
        Rfile = open(FTPFILES,'r')              # open the input file with settings
    except:
        print("ERROR: Cannot open file with file names.")
        return()

    try:
        txt = Rfile.readline()                  # read the next line
        DIRday = txt[0:-1]
    except:
        print("ERROR: Cannot read DIRday name.")
        return()

    TheEnd = False
    while (TheEnd == False):
        try:
            Title = Rfile.readline()            # read the next line
            Title = Title[0:-1]
            Textfile = Rfile.readline()         # read the next line
            Textfile = Textfile[0:-1]

            if Textfile != "":                  # A filename to be uploaded
                if TXTupload == True:
                    FTPfiles.append(Textfile)
                    print(Textfile)
            else:
                TheEnd = True 
        except:
            TheEnd = True

        if HTMLupload == True and TheEnd != True:   # HTML upload
            MakeHTML(Title, Textfile)               # Make a HTML file of the text file

    # Start FTP upload routine    
    ftp = None
 
    try:
        # ftp = ftplib.FTP(FTPhost, FTPuser, FTPpassword)           # Open the FTP connection for file uploading with the default time out, works OK for me
        ftp = ftplib.FTP(FTPhost, FTPuser, FTPpassword, "", 10)     # Open the FTP connection for file uploading with a time out, did avoid some problems for others
        print("Connected and logged in to FTP host")
    except:
        print("ERROR: Cannot connected and log in to FTP host")

    if (ftp):
        # Change FTP directory
        try:    
            if FTPdir != "":
                ftp.cwd(FTPdir)
                print("Changed to remote directory: " + FTPdir)
        except:
            print("ERROR: Cannot change to remote directory: " + FTPdir)
            
        # Upload the files
        n = 0
        while n < len(FTPfiles):
            filename = FTPfiles[n]
            storedname = DIRday + filename

            try:            
                fup = open(storedname, 'rb')                        # Open the file of the picture to be uploaded
                ftp.storbinary("STOR " + filename, fup, 8192)       # Store the file
                fup.close()
                print(filename + " uploaded")
            except:
                print("ERROR: " + filename + " upload FAILED")
            n = n + 1
    try:
        if ftp:
            ftp.close()
    except:
        pass

    t = time.time()
    T =time.gmtime(t)
    txt = strftime("%H:%M:%S", T)
    txt = txt + "-end FTP upload"
    print(txt)


# ================ Make HTML ================================================
def MakeHTML(Title, textfile):
    global FTPfiles
    global DIRday

    TextInput = DIRday + textfile
    file_name, file_extension = os.path.splitext(textfile)
    htmlUpload = file_name + ".htm"
    # print(Title, htmlUpload)
    htmlSave = DIRday + file_name + ".htm"
 
    try:
        Rfile = open(TextInput,'r')             # open the input file with text
    except:
        print("ERROR: Cannot open text file: ", TextInput)
        return()

    try:
        Wfile = open(htmlSave,'w')              # open the output file with html code
    except:
        print("ERROR: Cannot open html file: ", htmlSave)
        return()

    # Special characters: \n \r \"
    Wfile.write("<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0 Transitional//EN\">\n")
    Wfile.write("<HTML><HEAD><TITLE>DIGITAL SELECTIVE CALLING 8414.5 kHz</TITLE>\n")
    Wfile.write("<META content=\"text/html; charset=windows-1252\" http-equiv=Content-Type>\n")
    Wfile.write("</head>\n") 
    Wfile.write("<body style=\"background-color: #ffffd0; color: black\"><samp>\n")
    Wfile.write("<P style=\"text-align: center;font-size:1.5em;\"><B>" + Title + "</b></p>\n<hr>\n")

    TheEnd = False
    while (TheEnd == False):
        try:
            txt = Rfile.readline()              # read the next line
            if txt != "":
                txt = txt[0:-1] + "<br>\n"
                Wfile.write(txt)
            else:
                TheEnd = True
        except:
            TheEnd = True
    Wfile.write("</samp></body>\n")
    Wfile.write("</html>\n")
    Rfile.close()
    Wfile.close()

    FTPfiles.append(htmlUpload)
    print(htmlUpload)
   

CONTROL()                       # Start the main routine loop

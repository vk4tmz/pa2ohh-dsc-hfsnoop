
import os
import time

####################################################################
# Common Utility / Helper Functions - to be moved/refactored later
####################################################################

def makedirs(dirname:str):
    try:
        os.makedirs(dirname, exist_ok=True)
    except OSError as e:
        print(f"Error creating [{dirname}]. {e}")

def getTimeStamp():
    return time.strftime("%Y%m%d-%H:%M:%S", time.gmtime())

####################################################################
# DSC Specific Utility / Helper Functions - to be moved/refactored later
####################################################################

def getMsgPaddedVals(data, idx, length):
    txt = ""
    for N in range(idx,idx+length):
        v = getMsgVal(data, N)
        if v  < 10:
            txt += "0" 
        txt += str(v).strip()    
    
    return txt

# ... Try to read from msgData[] and return that value or 127 (EOS) if not possible ...
def getMsgVal(data, i):
    try:
        v = data[i]
    except:
        v = 127                         # Out of range of msgData[], return EOS (=127)
    return(v)

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
def fromTENunit(s: str):

    # We're expecting 10 bits to be check and converted
    if (len(s) != 10):
        return -255; # since we return -(val) if parity does not match, we return -255

    intB = 0
    v = 0
    if (s[0] == "Y"):
        v = v + 1
    else:
        intB += 1
    if (s[1] == "Y"):
        v = v + 2
    else:
        intB += 1
    if (s[2] == "Y"):
        v = v + 4
    else:
        intB += 1
    if (s[3] == "Y"):
        v = v + 8
    else:
        intB += 1
    if (s[4] == "Y"):
        v = v + 16
    else:
        intB += 1
    if (s[5] == "Y"):
        v = v + 32
    else:
        intB += 1
    if (s[6] == "Y"):
        v = v + 64
    else:
        intB += 1

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


import logging
import sys


from decoder.FSKDecoder import FSKDecoder
from utils import getMsgVal
from decoder.DSCMessage import DscMessage, DscSelectiveGeographicAreaMsg, DscDistressAlertMsg,\
            DscRoutineGroupCallMsg, DscAllShipCallMsg, DscSelectiveIndividualCallMsg,\
            DscSelectiveIndividualAutomaticCallMsg
from decoder.DSCExpansionMessageFactory import DSCExpansionMessageFactory
from decoder.Bits import BitQueue
from db.DSCDatabases import DscDatabases

FORMAT_SPECIFIERS = [102, 112, 114, 116, 120, 123]  # 
FORMAT_SPECIFIERS_SAME = [112, 116]                 # Distress and All Ships 

DEBUG = 0

class DSCMessageFactory:

    dscDB : DscDatabases
    bits: BitQueue
    expMsgFactory: DSCExpansionMessageFactory
    log: logging.Logger

    ensureFormatSpecifiersSame: bool = False

    def __init__(self, bits: BitQueue, dscDB : DscDatabases):
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))
        self.bits = bits
        self.dscDB = dscDB
        self.expMsgFactory = DSCExpansionMessageFactory()


    def getValSymbol(self, idx):
        return self.bits.getValSymbol(0, idx)

    def getMessageFrame(self, i:int, dest:list, errMsg:str):
        Vprevious = -1
        L3Berror = False
        msgData = []

        while(1):                           # Loop until a break occurs
            V = self.getValSymbol(i)
            if V < 0:
                V = self.getValSymbol(i+5)       # If 3 bits error check value incorrect, take the RTX signal 5 symbols later
            if V >= 0:
                msgData.append(V)           # If the value has a correct CRC value, add it to the data
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
            self.log.debug(f"{errMsg}")
            return False

        dest.extend(msgData)

        return True

    def frameDataAt(self, data:list, idx:int):
        if ((idx < 0) or (idx >= len(data))):
            return 127                      # Out of range of msgData[], return EOS (=127)

        return(data[idx])

    def checkFrameECC(self, data:list, errMsg:str):
        # ... Check errors with error check character ...
        ECC = self.frameDataAt(data, 0) 
        i = 1
        while i < (len(data) - 1):
            ECC = ECC ^ self.frameDataAt(data, i)
            i = i + 1

        if self.frameDataAt(data, len(data)-1) != ECC:  # The last value in the array msgData is the Error check symbol
            if DEBUG != 0:
                self.log.debug(f"{errMsg}")

            return False
        
        return True

    def processMessage(self): 
    
        # ... Check if the double transmission of the format specifier is identical ...
        fs1 = -1                # The 1st format specifier
        fs2 = -1                # The 2nd format specifier

        fs1 = self.getValSymbol(13)
        fs1rx = self.getValSymbol(14)
        if fs1 < 100:           # If incorrect error check bits (below -1) or not valid (below 100)
            fs1 = self.getValSymbol(18)

        fs2 = self.getValSymbol(15)
        fs2rx = self.getValSymbol(16)
        if fs2 < 100:           # If incorrect error check bits (below -1) or not valid (below 100)
            fs2 = self.getValSymbol(20)
        
        if not ((fs1 in FORMAT_SPECIFIERS) or (fs2 in FORMAT_SPECIFIERS_SAME)):
            self.log.debug(f"Invalid Format specifiers - fs1: [{fs1}]  fs2: [{fs2}]")
            return None

        # Checking the last 2 RX values of the Phasing Sequences
        #  - For now if since we have confirmed a DX Phase then we'll monitor and just warn.
        #    In Future we may enforce strictness check here.
        if ((fs1rx != 105) or (fs2rx != 104)):
            self.log.debug(f"Format specifiers Phasing RX aren't as expect - fs1rx: [{fs1rx}]  fs2rx: [{fs2rx}] - Continuing")


        # As per ITU DSC Spec:
        # 4.2 It is considered that receiver decoders must detect the format specifier character twice for
        #     “distress” alerts and “all ships” calls to effectively eliminate false alerting. For other calls, the
        #     address characters provide additional protection against false alerting and, therefore, single
        #     detection of the format specifier character is considered satisfactory (see Table 3).
        if ((fs1 in FORMAT_SPECIFIERS_SAME) or (fs2 in FORMAT_SPECIFIERS_SAME)):
            if (fs1 != fs2):
                if (self.ensureFormatSpecifiersSame):
                    self.log.debug(f"Format specifiers not identical - fs1: [{fs1}]  fs2: [{fs2}]")
                    return None
                else:
                    self.log.debug(f"Format specifiers not identical - fs1: [{fs1}]  fs2: [{fs2}] - Continuing")

        # ... Make the message data and store in msgData ...
        msgData = []                        # Clear the data
        msgData.append(fs1)                 # Append the format specifier
        i = 17                              # The message starts at position 17
        if not self.getMessageFrame(i, msgData, "Error Character Check 3 last bits (2x)"):
            return None

        if not self.checkFrameECC(msgData, "Data does not match with Error Check Character"):
            return None
    
        # ... Search for extension message ...
        startExpMsgIdx = i + 6                 # The possible start of the extension message
        V = self.getValSymbol(startExpMsgIdx)

        expMsgData = []
        if V >= 100 and V <= 106:              # Do we have EXPMSG    

            # ... Start to fill the expMsgData ....
            i = startExpMsgIdx                     # The possible extension message starts at this position

            if not self.getMessageFrame(i, expMsgData, "Error expansion msg, Error Character Check 3 last bits (2x)"):
                expMsgData = []                 # Clear the expMsgData
            elif not self.checkFrameECC(expMsgData, "Data expansion msg does not match with Error Check Character"):
                expMsgData = []

        return self.selectMessageDecoder(msgData, expMsgData)
    

    # ============================ Select the decoder depending on the Format specifier ==============================

    def selectMessageDecoder(self, msgData, expMsgData) -> DscMessage | None:
        
        fmtSpecId = getMsgVal(msgData, 0)

        self.log.debug(f"FSID: [{fmtSpecId}],  msgData: [{msgData}],  expMsgData: [{expMsgData}]")

        msg: DscMessage
        match fmtSpecId:
            case 102:               # Format specifier 102
                msg = DscSelectiveGeographicAreaMsg(msgData, expMsgData, self.dscDB)
            case 112:               # Format specifier 112
                msg = DscDistressAlertMsg(msgData, expMsgData, self.dscDB)
            case 114:               # Format specifier 114
                msg = DscRoutineGroupCallMsg(msgData, expMsgData, self.dscDB)
            case 116:               # Format specifier 116
                msg = DscAllShipCallMsg(msgData, expMsgData, self.dscDB)
            case 120:               # Format specifier 120
                msg = DscSelectiveIndividualCallMsg(msgData, expMsgData, self.dscDB)
            case 123:               # Format specifier 123
                msg = DscSelectiveIndividualAutomaticCallMsg(msgData, expMsgData, self.dscDB)
            case _:
                self.log.debug(f"Error or no supported format specifier: [{fmtSpecId}]")
                return None

        if (msg is None):
            return None

        if ((expMsgData is not None) and (len(expMsgData) != 0)):            # Decode the extension message
            msg.expMsgs = self.expMsgFactory.processMessages(expMsgData)


        return msg
        
    
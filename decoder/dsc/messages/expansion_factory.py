
import logging

from decoder.dsc.messages.expansion import DscEhancedPositionResolutionMsg, DscPositionSourceAndDatumMsg,\
        DscVesselCurrentSpeedMsg, DscVesselCurrentCourseMsg, DscAdditionalInformationMsg,\
        DscEnhancedGeographicAreaMsg, DscNumberPersonsOnBoardMsg, DscExpansionMessage
from util.utils import getMsgVal
from collections import deque

HLINE = "==================================="       # Message separation line

#######################################################################
#  class DSCExpansionMessageFactory
#######################################################################

class DSCExpansionMessageFactory:    

    def __init__(self) -> None:
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))


    # ============================ Decode Expansion message ==============================
    # Expansion message decoder ITU-R M.821

    def processMessages(self, expMsgData: list) -> list[DscExpansionMessage] :

        msgs: list[DscExpansionMessage] = []

        emq = deque(expMsgData)
        if len(emq) == 0:        # Return if no message
            self.isEmpty = True
            return msgs
        
        while(1):
            if len(emq) <= 0:         # Stop if the end of self.expMsgData[] has been reached
                break

            expSpecId = getMsgVal(emq, 0)
            if expSpecId in [117, 122, 127]:        # Stop if one of the 3 EOS characters
                break

            if expSpecId < 100 or expSpecId > 106:  # Stop if not a known expansion data specifier
                self.log.error(f"[{expSpecId}] Unknown expansion data specifier:")
                break

            msg = None
            emq.popleft()
            match expSpecId:
                case 100:
                    msg = DscEhancedPositionResolutionMsg(emq)
                case 101:
                    msg = DscPositionSourceAndDatumMsg(emq)
                case 102:
                    msg = DscVesselCurrentSpeedMsg(emq)
                case 103:
                    msg = DscVesselCurrentCourseMsg(emq)
                case 104:
                    msg = DscAdditionalInformationMsg(emq)
                case 105:
                    msg = DscEnhancedGeographicAreaMsg(emq)
                case 106:
                    msg = DscNumberPersonsOnBoardMsg(emq)

            if msg:
                msgs.append(msg)

        return msgs
    

    def print(self, msgs: list[DscExpansionMessage] , out: list):

        out.append(HLINE)
        out.append("Expansion message ITU-R M.821:")
        
        for msg in msgs:
            out.append(HLINE)
            msg.print(out);       

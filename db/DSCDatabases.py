
import logging

from DSCConfig import DscConfig
from db.CoastDB import CoastDB
from db.ShipDB import ShipDB
from db.MidsDB import MidsDB

class DscDatabases:

    log: logging.Logger
    dscCfg:DscConfig

    coastDB: CoastDB
    shipDB: ShipDB
    midsDB: MidsDB

    def __init__(self, dscCfg:DscConfig):
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))
        self.dscCfg = dscCfg

        self.coastDB = CoastDB(dscCfg)
        self.shipDB = ShipDB(dscCfg)
        self.midsDB = MidsDB(dscCfg)

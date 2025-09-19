from datetime import datetime
import uuid

from ..DataBase import (
    sqlSelect, sqlUpdate
)





class PeerShareLink:
    def __init__(self, ShareID: str, Configuration: str, Peer: str, ExpireDate: datetime, ShareDate: datetime):
        self.ShareID = ShareID
        self.Peer = Peer
        self.Configuration = Configuration
        self.ShareDate = ShareDate
        self.ExpireDate = ExpireDate

    def toJson(self):
        return {
            "ShareID": self.ShareID,
            "Peer": self.Peer,
            "Configuration": self.Configuration,
            "ExpireDate": self.ExpireDate
        }

class PeerShareLinks:
    def __init__(self):
        self.Links: list[PeerShareLink] = []
        # Check if table exists using PostgreSQL syntax
        existingTables = sqlSelect(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'PeerShareLinks'").fetchall()
        if len(existingTables) == 0:
            sqlUpdate(
                """
                    CREATE TABLE IF NOT EXISTS PeerShareLinks (
                        ShareID VARCHAR NOT NULL PRIMARY KEY, 
                        Configuration VARCHAR NOT NULL, 
                        Peer VARCHAR NOT NULL,
                        ExpireDate TIMESTAMP,
                        SharedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
            )
        self.__getSharedLinks()

    def __getSharedLinks(self):
        self.Links.clear()
        allLinks = sqlSelect(
            "SELECT * FROM PeerShareLinks WHERE ExpireDate IS NULL OR ExpireDate > CURRENT_TIMESTAMP").fetchall()
        for link in allLinks:
            self.Links.append(PeerShareLink(*link))

    def getLink(self, Configuration: str, Peer: str) -> list[PeerShareLink]:
        self.__getSharedLinks()
        return list(filter(lambda x: x.Configuration == Configuration and x.Peer == Peer, self.Links))

    def getLinkByID(self, ShareID: str) -> list[PeerShareLink]:
        self.__getSharedLinks()
        return list(filter(lambda x: x.ShareID == ShareID, self.Links))

    def addLink(self, Configuration: str, Peer: str, ExpireDate: datetime = None) -> tuple[bool, str]:
        try:
            newShareID = str(uuid.uuid4())
            if len(self.getLink(Configuration, Peer)) > 0:
                sqlUpdate(
                    "UPDATE PeerShareLinks SET ExpireDate = CURRENT_TIMESTAMP WHERE Configuration = %s AND Peer = %s",
                    (Configuration, Peer,))
            sqlUpdate("INSERT INTO PeerShareLinks (ShareID, Configuration, Peer, ExpireDate) VALUES (%s, %s, %s, %s)",
                      (newShareID, Configuration, Peer, ExpireDate,))
            self.__getSharedLinks()
        except Exception as e:
            return False, str(e)
        return True, newShareID

    def updateLinkExpireDate(self, ShareID, ExpireDate: datetime = None) -> tuple[bool, str]:
        sqlUpdate("UPDATE PeerShareLinks SET ExpireDate = %s WHERE ShareID = %s;", (ExpireDate, ShareID,))
        self.__getSharedLinks()
        return True, ""


AllPeerShareLinks: PeerShareLinks = PeerShareLinks()

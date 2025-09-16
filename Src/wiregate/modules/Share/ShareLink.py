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
        existingTables = sqlSelect(
            "SELECT name FROM sqlite_master WHERE type='table' and name = 'PeerShareLinks'").fetchall()
        if len(existingTables) == 0:
            sqlUpdate(
                """
                    CREATE TABLE PeerShareLinks (
                        ShareID VARCHAR NOT NULL PRIMARY KEY, Configuration VARCHAR NOT NULL, Peer VARCHAR NOT NULL,
                        ExpireDate DATETIME,
                        SharedDate DATETIME DEFAULT (datetime('now', 'localtime'))
                    )
                """
            )
        self.__getSharedLinks()

    def __getSharedLinks(self):
        self.Links.clear()
        allLinks = sqlSelect(
            "SELECT * FROM PeerShareLinks WHERE ExpireDate IS NULL OR ExpireDate > datetime('now', 'localtime')").fetchall()
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
                    "UPDATE PeerShareLinks SET ExpireDate = datetime('now', 'localtime') WHERE Configuration = ? AND Peer = ?",
                    (Configuration, Peer,))
            sqlUpdate("INSERT INTO PeerShareLinks (ShareID, Configuration, Peer, ExpireDate) VALUES (?, ?, ?, ?)",
                      (newShareID, Configuration, Peer, ExpireDate,))
            self.__getSharedLinks()
        except Exception as e:
            return False, str(e)
        return True, newShareID

    def updateLinkExpireDate(self, ShareID, ExpireDate: datetime = None) -> tuple[bool, str]:
        sqlUpdate("UPDATE PeerShareLinks SET ExpireDate = ? WHERE ShareID = ?;", (ExpireDate, ShareID,))
        self.__getSharedLinks()
        return True, ""


AllPeerShareLinks: PeerShareLinks = PeerShareLinks()

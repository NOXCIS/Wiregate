from datetime import datetime
import uuid
import logging

from ..DataBase import (
    sqlSelect, sqlUpdate
)

logger = logging.getLogger(__name__)





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
        # Use asyncio.run() since __init__ can't be async
        import asyncio
        asyncio.run(self._init_async())

    async def _init_async(self):
        """Async initialization"""
        # Check if table exists using database-agnostic approach
        from wiregate.modules.DataBase import get_redis_manager
        manager = await get_redis_manager()
        
        # Use the appropriate method based on database type
        if hasattr(manager, 'table_exists'):
            # PostgreSQL/Redis manager
            table_exists = manager.table_exists('PeerShareLinks')
        else:
            # SQLite manager - check using PRAGMA
            try:
                cursor = await sqlSelect("SELECT name FROM sqlite_master WHERE type='table' AND name='PeerShareLinks'")
                result = cursor.fetchall()
                table_exists = len(result) > 0
            except Exception as e:
                logger.warning(f"Failed to check if PeerShareLinks table exists: {e}")
                table_exists = False
        
        if not table_exists:
            await sqlUpdate(
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
        await self.__getSharedLinks()

    async def __getSharedLinks(self):
        self.Links.clear()
        cursor = await sqlSelect(
            "SELECT * FROM PeerShareLinks WHERE ExpireDate IS NULL OR ExpireDate > CURRENT_TIMESTAMP")
        allLinks = cursor.fetchall()
        for link in allLinks:
            self.Links.append(PeerShareLink(*link))

    async def getLink(self, Configuration: str, Peer: str) -> list[PeerShareLink]:
        await self.__getSharedLinks()
        return list(filter(lambda x: x.Configuration == Configuration and x.Peer == Peer, self.Links))

    async def getLinkByID(self, ShareID: str) -> list[PeerShareLink]:
        await self.__getSharedLinks()
        return list(filter(lambda x: x.ShareID == ShareID, self.Links))

    async def addLink(self, Configuration: str, Peer: str, ExpireDate: datetime = None) -> tuple[bool, str]:
        try:
            newShareID = str(uuid.uuid4())
            existing_links = await self.getLink(Configuration, Peer)
            if len(existing_links) > 0:
                await sqlUpdate(
                    "UPDATE PeerShareLinks SET ExpireDate = CURRENT_TIMESTAMP WHERE Configuration = %s AND Peer = %s",
                    (Configuration, Peer,))
            await sqlUpdate("INSERT INTO PeerShareLinks (ShareID, Configuration, Peer, ExpireDate) VALUES (%s, %s, %s, %s)",
                      (newShareID, Configuration, Peer, ExpireDate,))
            await self.__getSharedLinks()
        except Exception as e:
            return False, str(e)
        return True, newShareID

    async def updateLinkExpireDate(self, ShareID, ExpireDate: datetime = None) -> tuple[bool, str]:
        await sqlUpdate("UPDATE PeerShareLinks SET ExpireDate = %s WHERE ShareID = %s;", (ExpireDate, ShareID,))
        await self.__getSharedLinks()
        return True, ""


AllPeerShareLinks: PeerShareLinks = PeerShareLinks()

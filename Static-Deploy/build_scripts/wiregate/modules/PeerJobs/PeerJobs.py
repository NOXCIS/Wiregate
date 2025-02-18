import os
import sqlite3
from datetime import datetime
import json

from ..shared import sqlSelect

from .PeerJob import PeerJob
from .PeerJobLogger import PeerJobLogger
from ..config import CONFIGURATION_PATH


class PeerJobs:

    def __init__(self):
        self.Jobs: list[PeerJob] = []
        self.jobdb = sqlite3.connect(os.path.join(CONFIGURATION_PATH, 'db', 'wgdashboard_job.db'),
                                     check_same_thread=False)
        self.jobdb.row_factory = sqlite3.Row
        self.__createPeerJobsDatabase()
        self.__getJobs()

    def __getJobs(self):
        self.Jobs.clear()
        with self.jobdb:
            jobdbCursor = self.jobdb.cursor()
            jobs = jobdbCursor.execute("SELECT * FROM PeerJobs WHERE ExpireDate IS NULL").fetchall()
            for job in jobs:
                self.Jobs.append(PeerJob(
                    job['JobID'], job['Configuration'], job['Peer'], job['Field'], job['Operator'], job['Value'],
                    job['CreationDate'], job['ExpireDate'], job['Action']))

    def getAllJobs(self, configuration: str = None):
        if configuration is not None:
            with self.jobdb:
                jobdbCursor = self.jobdb.cursor()
                jobs = jobdbCursor.execute(
                    f"SELECT * FROM PeerJobs WHERE Configuration = ?", (configuration,)).fetchall()
                j = []
                for job in jobs:
                    j.append(PeerJob(
                        job['JobID'], job['Configuration'], job['Peer'], job['Field'], job['Operator'], job['Value'],
                        job['CreationDate'], job['ExpireDate'], job['Action']))
                return j
        return []

    def __createPeerJobsDatabase(self):
        with self.jobdb:
            jobdbCursor = self.jobdb.cursor()

            existingTable = jobdbCursor.execute("SELECT name from sqlite_master where type='table'").fetchall()
            existingTable = [t['name'] for t in existingTable]

            if "PeerJobs" not in existingTable:
                jobdbCursor.execute('''
                CREATE TABLE PeerJobs (JobID VARCHAR NOT NULL, Configuration VARCHAR NOT NULL, Peer VARCHAR NOT NULL,
                Field VARCHAR NOT NULL, Operator VARCHAR NOT NULL, Value VARCHAR NOT NULL, CreationDate DATETIME,
                ExpireDate DATETIME, Action VARCHAR NOT NULL, PRIMARY KEY (JobID))
                ''')
                self.jobdb.commit()

    def toJson(self):
        return [x.toJson() for x in self.Jobs]

    def searchJob(self, Configuration: str, Peer: str):
        return list(filter(lambda x: x.Configuration == Configuration and x.Peer == Peer, self.Jobs))

    def saveJob(self, Job: PeerJob) -> tuple[bool, list] | tuple[bool, str]:
        try:
            with self.jobdb:
                jobdbCursor = self.jobdb.cursor()

                if (len(str(Job.CreationDate))) == 0:
                    jobdbCursor.execute('''
                    INSERT INTO PeerJobs VALUES (?, ?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S','now'), NULL, ?)
                    ''', (Job.JobID, Job.Configuration, Job.Peer, Job.Field, Job.Operator, Job.Value, Job.Action,))
                    JobLogger.log(Job.JobID,
                                  Message=f"Job is created if {Job.Field} {Job.Operator} {Job.Value} then {Job.Action}")

                else:
                    currentJob = jobdbCursor.execute('SELECT * FROM PeerJobs WHERE JobID = ?', (Job.JobID,)).fetchone()
                    if currentJob is not None:
                        jobdbCursor.execute('''
                            UPDATE PeerJobs SET Field = ?, Operator = ?, Value = ?, Action = ? WHERE JobID = ?
                            ''', (Job.Field, Job.Operator, Job.Value, Job.Action, Job.JobID))
                        JobLogger.log(Job.JobID,
                                      Message=f"Job is updated from if {currentJob['Field']} {currentJob['Operator']} {currentJob['value']} then {currentJob['Action']}; to if {Job.Field} {Job.Operator} {Job.Value} then {Job.Action}")
                self.jobdb.commit()
                self.__getJobs()

            return True, list(
                filter(lambda x: x.Configuration == Job.Configuration and x.Peer == Job.Peer and x.JobID == Job.JobID,
                       self.Jobs))
        except Exception as e:
            return False, str(e)

    def deleteJob(self, Job: PeerJob) -> tuple[bool, list] | tuple[bool, str]:
        try:
            if (len(str(Job.CreationDate))) == 0:
                return False, "Job does not exist"
            with self.jobdb:
                jobdbCursor = self.jobdb.cursor()
                jobdbCursor.execute('''
                    UPDATE PeerJobs SET ExpireDate = strftime('%Y-%m-%d %H:%M:%S','now') WHERE JobID = ?
                ''', (Job.JobID,))
                self.jobdb.commit()
            JobLogger.log(Job.JobID, Message=f"Job is removed due to being deleted or finshed.")
            self.__getJobs()
            return True, list(
                filter(lambda x: x.Configuration == Job.Configuration and x.Peer == Job.Peer and x.JobID == Job.JobID,
                       self.Jobs))
        except Exception as e:
            return False, str(e)

    def updateJobConfigurationName(self, ConfigurationName: str, NewConfigurationName: str) -> tuple[bool, str]:
        try:
            with self.jobdb:
                jobdbCursor = self.jobdb.cursor()
                jobdbCursor.execute('''
                        UPDATE PeerJobs SET Configuration = ? WHERE Configuration = ?
                    ''', (NewConfigurationName, ConfigurationName,))
                self.jobdb.commit()
            self.__getJobs()
        except Exception as e:
            return False, str(e)

    def runJob(self):
        from ..Core import Configurations
        needToDelete = []
        for job in self.Jobs:
            c = Configurations.get(job.Configuration)
            if c is not None:
                if job.Field == "weekly":
                    current_time = datetime.now()
                    current_weekday = str(current_time.weekday())
                    current_time_str = current_time.strftime('%H:%M')
                    
                    schedules = job.Value.split(',')
                    should_restrict = False
                    
                    for schedule in schedules:
                        day = schedule.split(':')[0].strip()
                        times = ':'.join(schedule.split(':')[1:])
                        start_time, end_time = times.split('-')
                        
                        start_time = ':'.join(start_time.strip().split(':')[:2])
                        end_time = ':'.join(end_time.strip().split(':')[:2])
                        
                        if day == current_weekday and start_time <= current_time_str <= end_time:
                            should_restrict = True
                            break
                    
                    # Get restricted peers directly from SQL
                    restricted_peers = sqlSelect(f"SELECT id FROM '{c.Name}_restrict_access'").fetchall()
                    peer_in_restricted = job.Peer in [p[0] for p in restricted_peers]
                    
                    if should_restrict and not peer_in_restricted:
                        s = c.restrictPeers([job.Peer]).get_json()
                        if s['status'] is True:
                            JobLogger.log(job.JobID, s["status"],
                                      f"Peer {job.Peer} from {c.Name} is successfully restricted (weekly schedule)")
                    elif not should_restrict and peer_in_restricted:
                        s = c.allowAccessPeers([job.Peer]).get_json()
                        if s['status'] is True:
                            JobLogger.log(job.JobID, s["status"],
                                      f"Peer {job.Peer} from {c.Name} is successfully unrestricted (weekly schedule)")
                
                else:
                    # Handle non-weekly jobs as before
                    f, fp = c.searchPeer(job.Peer)
                    if f:
                        if job.Field in ["total_receive", "total_sent", "total_data"]:
                            s = job.Field.split("_")[1]
                            x: float = getattr(fp, f"total_{s}") + getattr(fp, f"cumu_{s}")
                            y: float = float(job.Value)
                            runAction: bool = self.__runJob_Compare(x, y, job.Operator)
                        else:
                            x: datetime = datetime.now()
                            y: datetime = datetime.strptime(job.Value, "%Y-%m-%d %H:%M:%S")
                            runAction: bool = self.__runJob_Compare(x, y, job.Operator)

                        if runAction:
                            s = False
                            if job.Action == "restrict":
                                s = c.restrictPeers([fp.id]).get_json()
                            elif job.Action == "delete":
                                s = c.deletePeers([fp.id]).get_json()
                            elif job.Action == "rate_limit":
                                try:
                                    rates = json.loads(job.Value)
                                    success = fp.set_rate_limit(
                                        rates['upload_rate'],
                                        rates['download_rate']
                                    )
                                    s = {"status": success, "message": "Rate limits applied successfully" if success else "Failed to apply rate limits"}
                                except Exception as e:
                                    s = {"status": False, "message": f"Failed to apply rate limits: {str(e)}"}

                            if s['status'] is True:
                                JobLogger.log(job.JobID, s["status"],
                                          f"Peer {fp.id} from {c.Name} is successfully {job.Action}ed.")
                                needToDelete.append(job)
                            else:
                                JobLogger.log(job.JobID, s["status"],
                                          f"Peer {fp.id} from {c.Name} failed {job.Action}ed.")
                    else:
                        needToDelete.append(job)
            else:
                needToDelete.append(job)

        # Only delete non-weekly jobs
        for j in needToDelete:
            if j.Field != "weekly":
                self.deleteJob(j)

    def __runJob_Compare(self, x: float | datetime | int, y: float | datetime | int, operator: str):
        """
        Compare two values based on the specified operator.
        
        Args:
            x: First value (current metric/date/weekday)
            y: Second value (threshold/target date/target weekday)
            operator: Comparison operator (eq, neq, lgt, lst)
            
        Returns:
            bool: Result of the comparison
        """
        # Handle weekly schedule comparison
        if isinstance(x, int) and isinstance(y, int):
            if operator == "eq":  # Exactly on this day
                return x == y
            if operator == "neq":  # Any day except this day
                return x != y
            if operator == "lgt":  # After this day in the week
                return (x - y) % 7 > 0
            if operator == "lst":  # Before this day in the week
                return (y - x) % 7 > 0
    
        # Handle existing date and float comparisons
        if operator == "eq":  # Equal
            return x == y
        if operator == "neq":  # Not equal
            return x != y
        if operator == "lgt":  # Greater than
            return x > y
        if operator == "lst":  # Less than
            return x < y


JobLogger = PeerJobLogger()
#AllPeerJobs: PeerJobs = PeerJobs()
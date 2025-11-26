import os
import logging
from datetime import datetime
import json
import uuid

from ..DataBase import sqlSelect, get_redis_manager, SQLiteDatabaseManager
from .PeerJob import PeerJob
from .PeerJobLogger import PeerJobLogger
from ..Config import CONFIGURATION_PATH, DASHBOARD_TYPE

logger = logging.getLogger('wiregate')

class PeerJobs:

    def __init__(self):
        self.Jobs: list[PeerJob] = []
        self.db_manager = None
        self._is_sqlite = False
        self._init_done = False
        
    async def _ensure_initialized(self):
        """Ensure database manager is initialized"""
        if not self._init_done:
            self.db_manager = await get_redis_manager()
            self._is_sqlite = isinstance(self.db_manager, SQLiteDatabaseManager)
            await self._initialize_database()
            await self.__getJobs()
            self._init_done = True
        
    async def _initialize_database(self):
        """Initialize database tables for jobs"""
        try:
            # Ensure jobs table exists
            if isinstance(self.db_manager, SQLiteDatabaseManager):
                if not await self.db_manager.table_exists('PeerJobs'):
                    logger.info("Creating PeerJobs table...")
                    await self.db_manager.create_jobs_table()
            else:
                if not self.db_manager.table_exists('PeerJobs'):
                    logger.info("Creating PeerJobs table...")
                    self.db_manager.create_jobs_table()
            logger.debug("PeerJobs table ready")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    def __get_next_job_id(self) -> str:
        """Generate next job ID"""
        try:
            job_id = str(uuid.uuid4())[:8]  # Use short UUID
            return job_id
        except Exception as e:
            logger.error(f"Failed to generate job ID: {e}")
            return str(datetime.now().timestamp())

    async def __getJobs(self):
        logger.debug(f"__getJobs called, clearing {len(self.Jobs)} existing jobs")
        self.Jobs.clear()
        try:
            # Get all jobs from database
            if isinstance(self.db_manager, SQLiteDatabaseManager):
                records = await self.db_manager.get_all_records('PeerJobs')
            else:
                records = self.db_manager.get_all_records('PeerJobs')
            
            for record in records:
                try:
                    job = PeerJob(
                        record.get('JobID'),
                        record.get('Configuration'),
                        record.get('Peer'),
                        record.get('Field'),
                        record.get('Operator'),
                        record.get('Value'),
                        record.get('CreationDate'),
                        record.get('ExpireDate'),
                        record.get('Action')
                    )
                    self.Jobs.append(job)
                except Exception as e:
                    logger.warning(f"Failed to parse job record: {e}")
                    continue
            
            logger.debug(f"Loaded {len(self.Jobs)} jobs from database")
        except Exception as e:
            logger.error(f"Error loading jobs: {e}")
            return

    def getAllJobs(self, configuration: str = None):
        if configuration is not None:
            return [job for job in self.Jobs if job.Configuration == configuration]
        return self.Jobs

    def __createPeerJobsDatabase(self):
        # No longer needed with Redis - schema is implicit
        pass

    def toJson(self):
        return [x.toJson() for x in self.Jobs]

    def searchJob(self, Configuration: str, Peer: str):
        logger.debug(f" searchJob called for Configuration: {Configuration}, Peer: {Peer}")
        logger.debug(f" Searching in {len(self.Jobs)} total jobs")
        matching_jobs = list(filter(lambda x: x.Configuration == Configuration and x.Peer == Peer, self.Jobs))
        logger.debug(f" Found {len(matching_jobs)} matching jobs")
        for i, job in enumerate(matching_jobs):
            logger.debug(f"   Matching job {i+1}: {job.toJson()}")
        return matching_jobs

    async def saveJob(self, Job: PeerJob) -> tuple[bool, list] | tuple[bool, str]:
        await self._ensure_initialized()
        try:
            # Generate job ID if new or if it's a UUID (frontend generated)
            if not Job.JobID or (isinstance(Job.JobID, str) and len(Job.JobID) > 10):
                # If it's a UUID or empty, generate a new numeric ID
                Job.JobID = self.__get_next_job_id()
                Job.CreationDate = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            elif not Job.CreationDate:
                # If job ID exists but no creation date, it's a new job
                Job.CreationDate = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Prepare job data
            job_data = {
                'id': Job.JobID,  # Use JobID as the primary key
                'JobID': Job.JobID,
                'Configuration': Job.Configuration,
                'Peer': Job.Peer,
                'Field': Job.Field,
                'Operator': Job.Operator,
                'Value': Job.Value,
                'CreationDate': Job.CreationDate,
                'ExpireDate': Job.ExpireDate,
                'Action': Job.Action
            }

            # Save to database
            if isinstance(self.db_manager, SQLiteDatabaseManager):
                await self.db_manager.insert_record('PeerJobs', Job.JobID, job_data)
            else:
                self.db_manager.insert_record('PeerJobs', Job.JobID, job_data)

            # Log the action
            if Job.CreationDate == datetime.now().strftime('%Y-%m-%d %H:%M:%S'):
                await JobLogger.log(Job.JobID, Message=f"Job created: if {Job.Field} {Job.Operator} {Job.Value} then {Job.Action}")
            else:
                await JobLogger.log(Job.JobID, Message=f"Job updated: if {Job.Field} {Job.Operator} {Job.Value} then {Job.Action}")

            # Reload jobs
            await self.__getJobs()

            return True, [job for job in self.Jobs if job.JobID == Job.JobID]

        except Exception as e:
            return False, str(e)

    async def deleteJob(self, Job: PeerJob) -> tuple[bool, list] | tuple[bool, str]:
        await self._ensure_initialized()
        try:
            if not Job.JobID:
                return False, "Job does not exist"

            # Check if job exists
            if isinstance(self.db_manager, SQLiteDatabaseManager):
                record = await self.db_manager.get_record('PeerJobs', Job.JobID)
            else:
                record = self.db_manager.get_record('PeerJobs', Job.JobID)
            
            if record:
                # Log the deletion before removing
                await JobLogger.log(Job.JobID, Message="Job deleted by user")
                
                # Actually remove from database
                if isinstance(self.db_manager, SQLiteDatabaseManager):
                    await self.db_manager.delete_record('PeerJobs', Job.JobID)
                else:
                    self.db_manager.delete_record('PeerJobs', Job.JobID)
                
                # Reload jobs
                await self.__getJobs()
                
                return True, []
            else:
                return False, "Job not found"

        except Exception as e:
            return False, str(e)

    async def updateJobConfigurationName(self, ConfigurationName: str, NewConfigurationName: str) -> tuple[bool, str]:
        await self._ensure_initialized()
        try:
            # Get all jobs for this configuration
            if isinstance(self.db_manager, SQLiteDatabaseManager):
                records = await self.db_manager.get_all_records('PeerJobs')
            else:
                records = self.db_manager.get_all_records('PeerJobs')
            
            updated_count = 0
            
            for record in records:
                if record.get('Configuration') == ConfigurationName:
                    record['Configuration'] = NewConfigurationName
                    if isinstance(self.db_manager, SQLiteDatabaseManager):
                        await self.db_manager.update_record('PeerJobs', record.get('JobID'), record)
                    else:
                        self.db_manager.update_record('PeerJobs', record.get('JobID'), record)
                    updated_count += 1

            # Reload jobs
            await self.__getJobs()
            return True, f"Updated {updated_count} jobs"

        except Exception as e:
            return False, str(e)

    async def runJob(self):
        await self._ensure_initialized()
        from ..Core import Configurations
        needToDelete = []
        
        logger.debug(f"Running {len(self.Jobs)} jobs")
        
        for job in self.Jobs:
            try:
                c = Configurations.get(job.Configuration)
                if c is None:
                    logger.warning(f"Configuration {job.Configuration} not found for job {job.JobID}")
                    needToDelete.append(job)
                    continue
                
                if job.Field == "weekly":
                    await self._runWeeklyJob(job, c)
                else:
                    should_delete = await self._runNonWeeklyJob(job, c)
                    if should_delete:
                        needToDelete.append(job)
                        
            except Exception as e:
                logger.error(f"Error running job {job.JobID}: {e}")
                await JobLogger.log(job.JobID, False, f"Job execution failed: {str(e)}")
                # Don't delete jobs that failed due to errors, just log them

        # Only delete non-weekly jobs that completed successfully
        for j in needToDelete:
            if j.Field != "weekly":
                logger.debug(f"Deleting completed job {j.JobID}")
                await self.deleteJob(j)
    
    async def _runWeeklyJob(self, job, configuration):
        """Handle weekly schedule jobs"""
        try:
            current_time = datetime.now()
            current_weekday = str(current_time.weekday())
            current_time_str = current_time.strftime('%H:%M')
            
            schedules = job.Value.split(',')
            should_restrict = False
            
            for schedule in schedules:
                try:
                    day = schedule.split(':')[0].strip()
                    times = ':'.join(schedule.split(':')[1:])
                    start_time, end_time = times.split('-')
                    
                    start_time = ':'.join(start_time.strip().split(':')[:2])
                    end_time = ':'.join(end_time.strip().split(':')[:2])
                    
                    if day == current_weekday and start_time <= current_time_str <= end_time:
                        should_restrict = True
                        break
                except Exception as e:
                    logger.warning(f"Error parsing schedule {schedule}: {e}")
                    continue
            
            # Get restricted peers directly from database
            restricted_peers = await configuration.db.get_restricted_peers()
            peer_in_restricted = job.Peer in [p.get('id') for p in restricted_peers]
            
            if should_restrict and not peer_in_restricted:
                result = await configuration.restrictPeersAsync([job.Peer])
                # Handle both dict (FastAPI) and Flask response
                s = result.get_json() if hasattr(result, 'get_json') else result
                if s['status'] is True:
                    await JobLogger.log(job.JobID, s["status"],
                              f"Peer {job.Peer} from {configuration.Name} is successfully restricted (weekly schedule)")
                else:
                    await JobLogger.log(job.JobID, s["status"],
                              f"Failed to restrict peer {job.Peer}: {s.get('message', 'Unknown error')}")
            elif not should_restrict and peer_in_restricted:
                result = await configuration.allowAccessPeersAsync([job.Peer])
                # Handle both dict (FastAPI) and Flask response
                s = result.get_json() if hasattr(result, 'get_json') else result
                if s['status'] is True:
                    await JobLogger.log(job.JobID, s["status"],
                              f"Peer {job.Peer} from {configuration.Name} is successfully unrestricted (weekly schedule)")
                else:
                    await JobLogger.log(job.JobID, s["status"],
                              f"Failed to unrestrict peer {job.Peer}: {s.get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error in weekly job {job.JobID}: {e}")
            await JobLogger.log(job.JobID, False, f"Weekly job execution failed: {str(e)}")
    
    async def _runNonWeeklyJob(self, job, configuration):
        """Handle non-weekly jobs (data usage, date-based)"""
        try:
            f, fp = configuration.searchPeer(job.Peer)
            if not f:
                logger.warning(f"Peer {job.Peer} not found in configuration {configuration.Name}")
                return True  # Delete job if peer doesn't exist
            
            if job.Field in ["total_receive", "total_sent", "total_data"]:
                s = job.Field.split("_")[1]
                x: float = getattr(fp, f"total_{s}") + getattr(fp, f"cumu_{s}")
                try:
                    if job.Action == "rate_limit":
                        rates = json.loads(job.Value)
                        y: float = float(rates.get('threshold', 0))
                    else:
                        y: float = float(job.Value)
                    runAction: bool = self.__runJob_Compare(x, y, job.Operator)
                except (ValueError, json.JSONDecodeError) as e:
                    logger.error(f"Invalid value format for job {job.JobID}: {e}")
                    return True  # Delete malformed job
            else:
                try:
                    x: datetime = datetime.now()
                    y: datetime = datetime.strptime(job.Value, "%Y-%m-%d %H:%M:%S")
                    runAction: bool = self.__runJob_Compare(x, y, job.Operator)
                except ValueError as e:
                    logger.error(f"Invalid date format for job {job.JobID}: {e}")
                    return True  # Delete malformed job

            if runAction:
                s = {"status": False, "message": "Unknown action"}
                
                if job.Action == "restrict":
                    result = await configuration.restrictPeersAsync([fp.id])
                    # Handle both dict (FastAPI) and Flask response
                    s = result.get_json() if hasattr(result, 'get_json') else result
                elif job.Action == "delete":
                    result = await configuration.deletePeersAsync([fp.id])
                    # Handle both dict (FastAPI) and Flask response
                    s = result.get_json() if hasattr(result, 'get_json') else result
                elif job.Action == "rate_limit":
                    try:
                        rates = json.loads(job.Value)
                        success = fp.set_rate_limit(
                            rates.get('upload_rate', 0),
                            rates.get('download_rate', 0)
                        )
                        s = {"status": success, "message": "Rate limits applied successfully" if success else "Failed to apply rate limits"}
                    except Exception as e:
                        s = {"status": False, "message": f"Failed to apply rate limits: {str(e)}"}

                if s['status'] is True:
                    await JobLogger.log(job.JobID, s["status"],
                              f"Peer {fp.id} from {configuration.Name} is successfully {job.Action}ed.")
                    return True  # Delete completed job
                else:
                    await JobLogger.log(job.JobID, s["status"],
                              f"Peer {fp.id} from {configuration.Name} failed {job.Action}ed: {s.get('message', 'Unknown error')}")
                    return False  # Keep job for retry
            else:
                logger.debug(f" Job {job.JobID} condition not met, keeping job")
                return False  # Keep job
                
        except Exception as e:
            logger.error(f"Error in non-weekly job {job.JobID}: {e}")
            await JobLogger.log(job.JobID, False, f"Non-weekly job execution failed: {str(e)}")
            return False  # Keep job for retry

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

    async def cleanupExpiredJobs(self, max_age_days=30):
        """Remove jobs older than max_age_days from database"""
        await self._ensure_initialized()
        try:
            if not self.db_manager:
                logger.error("Database manager not available for cleanup")
                return False, "Database manager not available"
            
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            cutoff_str = cutoff_date.strftime('%Y-%m-%d %H:%M:%S')
            
            if isinstance(self.db_manager, SQLiteDatabaseManager):
                records = await self.db_manager.get_all_records('PeerJobs')
            else:
                records = self.db_manager.get_all_records('PeerJobs')
            
            removed_count = 0
            
            for record in records:
                try:
                    creation_date = record.get('CreationDate', '')
                    
                    # Remove jobs older than cutoff date
                    if creation_date and creation_date < cutoff_str:
                        if isinstance(self.db_manager, SQLiteDatabaseManager):
                            await self.db_manager.delete_record('PeerJobs', record.get('JobID'))
                        else:
                            self.db_manager.delete_record('PeerJobs', record.get('JobID'))
                        removed_count += 1
                        logger.debug(f" Removed expired job {record.get('JobID')} (created: {creation_date})")
                        
                except Exception as e:
                    logger.warning(f"Error processing job {record.get('JobID')} during cleanup: {e}")
                    continue
            
            # Reload jobs after cleanup
            await self.__getJobs()
            
            logger.debug(f" Cleanup completed: removed {removed_count} expired jobs")
            return True, f"Removed {removed_count} expired jobs"
            
        except Exception as e:
            logger.error(f"Error during job cleanup: {e}")
            return False, str(e)

    async def getJobStats(self):
        """Get statistics about jobs in the system"""
        await self._ensure_initialized()
        try:
            if not self.db_manager:
                return {"error": "Database manager not available"}
            
            if isinstance(self.db_manager, SQLiteDatabaseManager):
                records = await self.db_manager.get_all_records('PeerJobs')
            else:
                records = self.db_manager.get_all_records('PeerJobs')
            
            stats = {
                "total_jobs": len(records),
                "active_jobs": len(self.Jobs),
                "expired_jobs": 0,
                "by_field": {},
                "by_action": {},
                "by_configuration": {}
            }
            
            for record in records:
                try:
                    # Count expired jobs
                    if record.get('ExpireDate'):
                        stats["expired_jobs"] += 1
                    
                    # Count by field
                    field = record.get('Field', 'unknown')
                    stats["by_field"][field] = stats["by_field"].get(field, 0) + 1
                    
                    # Count by action
                    action = record.get('Action', 'unknown')
                    stats["by_action"][action] = stats["by_action"].get(action, 0) + 1
                    
                    # Count by configuration
                    config = record.get('Configuration', 'unknown')
                    stats["by_configuration"][config] = stats["by_configuration"].get(config, 0) + 1
                    
                except Exception as e:
                    logger.warning(f"Error processing job {record.get('JobID')} for stats: {e}")
                    continue
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting job stats: {e}")
            return {"error": str(e)}


JobLogger = PeerJobLogger()
AllPeerJobs: PeerJobs = PeerJobs()

# Initialize jobs asynchronously - call this at startup
async def initialize_peer_jobs():
    """Initialize peer jobs asynchronously"""
    await AllPeerJobs._ensure_initialized()
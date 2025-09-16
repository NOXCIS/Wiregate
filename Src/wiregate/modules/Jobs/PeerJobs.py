import os
import logging
from datetime import datetime
import json

from ..DataBase import sqlSelect, get_redis_manager
from .PeerJob import PeerJob
from .PeerJobLogger import PeerJobLogger
from ..ConfigEnv import CONFIGURATION_PATH

logger = logging.getLogger('wiregate')

class MockRedisClient:
    """Mock Redis client for when Redis is not available"""
    def __init__(self):
        self._data = {}
    
    def exists(self, key):
        return key in self._data
    
    def set(self, key, value):
        self._data[key] = value
    
    def incr(self, key):
        if key not in self._data:
            self._data[key] = 0
        self._data[key] += 1
        return self._data[key]
    
    def hset(self, key, field, value):
        if key not in self._data:
            self._data[key] = {}
        self._data[key][field] = value
    
    def hgetall(self, key):
        return self._data.get(key, {})
    
    def lpush(self, key, value):
        if key not in self._data:
            self._data[key] = []
        self._data[key].insert(0, value)
    
    def lrange(self, key, start, end):
        data = self._data.get(key, [])
        if end == -1:
            return data[start:]
        return data[start:end+1]
    
    def hkeys(self, key):
        data = self._data.get(key, {})
        return list(data.keys())

class PeerJobs:

    def __init__(self):
        self.Jobs: list[PeerJob] = []
        self.redis_manager = None
        self.jobs_key = "wiregate:peer_jobs"
        self.job_counter_key = "wiregate:peer_jobs:counter"
        self._initialized = False
        self._ensure_redis_connection()
        self.__getJobs()
        
    def _ensure_redis_connection(self):
        """Ensure Redis connection is established"""
        if self.redis_manager is None:
            try:
                self.redis_manager = get_redis_manager()
                self.__initialize_redis()
                self._initialized = True
            except Exception as e:
                print(f"Warning: Could not connect to Redis: {e}")
                # Create a mock redis manager for fallback
                class MockRedisManager:
                    def __init__(self):
                        self.redis_client = MockRedisClient()
                self.redis_manager = MockRedisManager()
                self._initialized = True

    def __initialize_redis(self):
        """Initialize Redis with job counter if not exists"""
        if not self.redis_manager.redis_client.exists(self.job_counter_key):
            self.redis_manager.redis_client.set(self.job_counter_key, 0)

    def __get_next_job_id(self) -> str:
        """Generate next job ID using Redis counter"""
        self._ensure_redis_connection()
        return str(self.redis_manager.redis_client.incr(self.job_counter_key))

    def __getJobs(self):
        logger.debug(f"__getJobs called, clearing {len(self.Jobs)} existing jobs")
        self.Jobs.clear()
        try:
            # Check Redis connection
            if not self.redis_manager or not self.redis_manager.redis_client:
                print("[ERROR] Redis connection not available")
                return
            
            # Get all job keys
            job_keys = self.redis_manager.redis_client.hkeys(self.jobs_key)
            logger.debug(f"Found {len(job_keys)} job keys in Redis")
            
            for job_key in job_keys:
                try:
                    job_data = self.redis_manager.redis_client.hget(self.jobs_key, job_key)
                    if job_data:
                        job_dict = json.loads(job_data)
                        logger.debug(f" Loading job {job_key}: {job_dict}")
                        
                        # Validate job data structure
                        required_fields = ['JobID', 'Configuration', 'Peer', 'Field', 'Operator', 'Value', 'Action']
                        if not all(field in job_dict for field in required_fields):
                            print(f"[WARNING] Skipping malformed job {job_key}: missing required fields")
                            continue
                        
                        # Only load non-expired jobs (ExpireDate should be None, empty string, or not present)
                        expire_date = job_dict.get('ExpireDate')
                        if not expire_date or expire_date == "":
                            job_obj = PeerJob(
                                job_dict['JobID'],
                                job_dict['Configuration'],
                                job_dict['Peer'],
                                job_dict['Field'],
                                job_dict['Operator'],
                                job_dict['Value'],
                                job_dict.get('CreationDate', ''),
                                job_dict.get('ExpireDate', ''),
                                job_dict['Action']
                            )
                            self.Jobs.append(job_obj)
                            logger.debug(f" Added job: {job_obj.toJson()}")
                        else:
                            logger.debug(f" Skipping expired job: {job_key}")
                except json.JSONDecodeError as e:
                    print(f"[ERROR] Failed to parse job data for {job_key}: {e}")
                    continue
                except Exception as e:
                    print(f"[ERROR] Error processing job {job_key}: {e}")
                    continue
        except Exception as e:
            print(f"[ERROR] Critical error loading jobs: {e}")
            # Don't raise the exception, just log it and continue with empty jobs list
        
        logger.debug(f" __getJobs completed, now have {len(self.Jobs)} jobs")

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

    def saveJob(self, Job: PeerJob) -> tuple[bool, list] | tuple[bool, str]:
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

            # Save to Redis
            self.redis_manager.redis_client.hset(
                self.jobs_key, 
                Job.JobID, 
                json.dumps(job_data)
            )

            # Log the action
            if Job.CreationDate == datetime.now().strftime('%Y-%m-%d %H:%M:%S'):
                JobLogger.log(Job.JobID, Message=f"Job created: if {Job.Field} {Job.Operator} {Job.Value} then {Job.Action}")
            else:
                JobLogger.log(Job.JobID, Message=f"Job updated: if {Job.Field} {Job.Operator} {Job.Value} then {Job.Action}")

            # Reload jobs
            self.__getJobs()

            return True, [job for job in self.Jobs if job.JobID == Job.JobID]

        except Exception as e:
            return False, str(e)

    def deleteJob(self, Job: PeerJob) -> tuple[bool, list] | tuple[bool, str]:
        try:
            if not Job.JobID:
                return False, "Job does not exist"

            # Check if job exists
            job_data = self.redis_manager.redis_client.hget(self.jobs_key, Job.JobID)
            if job_data:
                # Log the deletion before removing
                JobLogger.log(Job.JobID, Message="Job deleted by user")
                
                # Actually remove from Redis
                self.redis_manager.redis_client.hdel(self.jobs_key, Job.JobID)
                
                # Reload jobs
                self.__getJobs()
                
                return True, []
            else:
                return False, "Job not found"

        except Exception as e:
            return False, str(e)

    def updateJobConfigurationName(self, ConfigurationName: str, NewConfigurationName: str) -> tuple[bool, str]:
        try:
            # Get all jobs for this configuration
            job_keys = self.redis_manager.redis_client.hkeys(self.jobs_key)
            updated_count = 0
            
            for job_key in job_keys:
                job_data = self.redis_manager.redis_client.hget(self.jobs_key, job_key)
                if job_data:
                    job_dict = json.loads(job_data)
                    if job_dict.get('Configuration') == ConfigurationName:
                        job_dict['Configuration'] = NewConfigurationName
                        self.redis_manager.redis_client.hset(
                            self.jobs_key, 
                            job_key, 
                            json.dumps(job_dict)
                        )
                        updated_count += 1

            # Reload jobs
            self.__getJobs()
            return True, f"Updated {updated_count} jobs"

        except Exception as e:
            return False, str(e)

    def runJob(self):
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
                    self._runWeeklyJob(job, c)
                else:
                    should_delete = self._runNonWeeklyJob(job, c)
                    if should_delete:
                        needToDelete.append(job)
                        
            except Exception as e:
                logger.error(f"Error running job {job.JobID}: {e}")
                JobLogger.log(job.JobID, False, f"Job execution failed: {str(e)}")
                # Don't delete jobs that failed due to errors, just log them

        # Only delete non-weekly jobs that completed successfully
        for j in needToDelete:
            if j.Field != "weekly":
                logger.debug(f"Deleting completed job {j.JobID}")
                self.deleteJob(j)
    
    def _runWeeklyJob(self, job, configuration):
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
                    print(f"[WARNING] Error parsing schedule {schedule}: {e}")
                    continue
            
            # Get restricted peers directly from Redis
            restricted_peers = configuration.db.get_restricted_peers()
            peer_in_restricted = job.Peer in [p.get('id') for p in restricted_peers]
            
            if should_restrict and not peer_in_restricted:
                s = configuration.restrictPeers([job.Peer]).get_json()
                if s['status'] is True:
                    JobLogger.log(job.JobID, s["status"],
                              f"Peer {job.Peer} from {configuration.Name} is successfully restricted (weekly schedule)")
                else:
                    JobLogger.log(job.JobID, s["status"],
                              f"Failed to restrict peer {job.Peer}: {s.get('message', 'Unknown error')}")
            elif not should_restrict and peer_in_restricted:
                s = configuration.allowAccessPeers([job.Peer]).get_json()
                if s['status'] is True:
                    JobLogger.log(job.JobID, s["status"],
                              f"Peer {job.Peer} from {configuration.Name} is successfully unrestricted (weekly schedule)")
                else:
                    JobLogger.log(job.JobID, s["status"],
                              f"Failed to unrestrict peer {job.Peer}: {s.get('message', 'Unknown error')}")
        except Exception as e:
            print(f"[ERROR] Error in weekly job {job.JobID}: {e}")
            JobLogger.log(job.JobID, False, f"Weekly job execution failed: {str(e)}")
    
    def _runNonWeeklyJob(self, job, configuration):
        """Handle non-weekly jobs (data usage, date-based)"""
        try:
            f, fp = configuration.searchPeer(job.Peer)
            if not f:
                print(f"[WARNING] Peer {job.Peer} not found in configuration {configuration.Name}")
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
                    print(f"[ERROR] Invalid value format for job {job.JobID}: {e}")
                    return True  # Delete malformed job
            else:
                try:
                    x: datetime = datetime.now()
                    y: datetime = datetime.strptime(job.Value, "%Y-%m-%d %H:%M:%S")
                    runAction: bool = self.__runJob_Compare(x, y, job.Operator)
                except ValueError as e:
                    print(f"[ERROR] Invalid date format for job {job.JobID}: {e}")
                    return True  # Delete malformed job

            if runAction:
                s = {"status": False, "message": "Unknown action"}
                
                if job.Action == "restrict":
                    s = configuration.restrictPeers([fp.id]).get_json()
                elif job.Action == "delete":
                    s = configuration.deletePeers([fp.id]).get_json()
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
                    JobLogger.log(job.JobID, s["status"],
                              f"Peer {fp.id} from {configuration.Name} is successfully {job.Action}ed.")
                    return True  # Delete completed job
                else:
                    JobLogger.log(job.JobID, s["status"],
                              f"Peer {fp.id} from {configuration.Name} failed {job.Action}ed: {s.get('message', 'Unknown error')}")
                    return False  # Keep job for retry
            else:
                logger.debug(f" Job {job.JobID} condition not met, keeping job")
                return False  # Keep job
                
        except Exception as e:
            print(f"[ERROR] Error in non-weekly job {job.JobID}: {e}")
            JobLogger.log(job.JobID, False, f"Non-weekly job execution failed: {str(e)}")
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

    def cleanupExpiredJobs(self, max_age_days=30):
        """Remove jobs older than max_age_days from Redis"""
        try:
            if not self.redis_manager or not self.redis_manager.redis_client:
                print("[ERROR] Redis connection not available for cleanup")
                return False, "Redis connection not available"
            
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            cutoff_str = cutoff_date.strftime('%Y-%m-%d %H:%M:%S')
            
            job_keys = self.redis_manager.redis_client.hkeys(self.jobs_key)
            removed_count = 0
            
            for job_key in job_keys:
                try:
                    job_data = self.redis_manager.redis_client.hget(self.jobs_key, job_key)
                    if job_data:
                        job_dict = json.loads(job_data)
                        creation_date = job_dict.get('CreationDate', '')
                        
                        # Remove jobs older than cutoff date
                        if creation_date and creation_date < cutoff_str:
                            self.redis_manager.redis_client.hdel(self.jobs_key, job_key)
                            removed_count += 1
                            logger.debug(f" Removed expired job {job_key} (created: {creation_date})")
                            
                except Exception as e:
                    print(f"[WARNING] Error processing job {job_key} during cleanup: {e}")
                    continue
            
            # Reload jobs after cleanup
            self.__getJobs()
            
            logger.debug(f" Cleanup completed: removed {removed_count} expired jobs")
            return True, f"Removed {removed_count} expired jobs"
            
        except Exception as e:
            print(f"[ERROR] Error during job cleanup: {e}")
            return False, str(e)

    def getJobStats(self):
        """Get statistics about jobs in the system"""
        try:
            if not self.redis_manager or not self.redis_manager.redis_client:
                return {"error": "Redis connection not available"}
            
            job_keys = self.redis_manager.redis_client.hkeys(self.jobs_key)
            stats = {
                "total_jobs": len(job_keys),
                "active_jobs": len(self.Jobs),
                "expired_jobs": 0,
                "by_field": {},
                "by_action": {},
                "by_configuration": {}
            }
            
            for job_key in job_keys:
                try:
                    job_data = self.redis_manager.redis_client.hget(self.jobs_key, job_key)
                    if job_data:
                        job_dict = json.loads(job_data)
                        
                        # Count expired jobs
                        if job_dict.get('ExpireDate'):
                            stats["expired_jobs"] += 1
                        
                        # Count by field
                        field = job_dict.get('Field', 'unknown')
                        stats["by_field"][field] = stats["by_field"].get(field, 0) + 1
                        
                        # Count by action
                        action = job_dict.get('Action', 'unknown')
                        stats["by_action"][action] = stats["by_action"].get(action, 0) + 1
                        
                        # Count by configuration
                        config = job_dict.get('Configuration', 'unknown')
                        stats["by_configuration"][config] = stats["by_configuration"].get(config, 0) + 1
                        
                except Exception as e:
                    print(f"[WARNING] Error processing job {job_key} for stats: {e}")
                    continue
            
            return stats
            
        except Exception as e:
            print(f"[ERROR] Error getting job stats: {e}")
            return {"error": str(e)}


JobLogger = PeerJobLogger()
AllPeerJobs: PeerJobs = PeerJobs()
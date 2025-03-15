from flask import Blueprint, request
import json
from datetime import datetime


from ..modules.App import ResponseObject

from ..modules.Jobs.PeerJobLogger import JobLogger

from ..modules.Jobs.PeerJob import PeerJob
from ..modules.Jobs.PeerJobs import AllPeerJobs
from ..modules.Core import Configurations


peer_jobs_blueprint = Blueprint('peer_jobs_api', __name__)

@peer_jobs_blueprint.post('/savePeerScheduleJob/')
def API_savePeerScheduleJob():
    data = request.json
    print(f"\n[DEBUG] Received job data: {json.dumps(data, indent=2)}")
    
    if "Job" not in data.keys():
        return ResponseObject(False, "Please specify job")
    job: dict = data['Job']
    
    # Validate rate limit action
    if job['Action'] == 'rate_limit':
        try:
            rates = json.loads(job.get('Value', '{}'))
            if not isinstance(rates, dict) or 'upload_rate' not in rates or 'download_rate' not in rates:
                return ResponseObject(False, "Invalid rate limit format. Must specify upload_rate and download_rate")
            
            # Validate rate values are positive numbers
            if not isinstance(rates['upload_rate'], (int, float)) or rates['upload_rate'] < 0:
                return ResponseObject(False, "Upload rate must be a positive number")
            if not isinstance(rates['download_rate'], (int, float)) or rates['download_rate'] < 0:
                return ResponseObject(False, "Download rate must be a positive number")
                
        except json.JSONDecodeError:
            return ResponseObject(False, "Invalid rate limit format")
    
    # Validate weekly schedule format
    if job['Field'] == 'weekly':
        print(f"\n[DEBUG] Processing weekly schedule. Value: {job['Value']}")
        try:
            if not job['Value']:
                return ResponseObject(False, "Weekly schedule cannot be empty")
                
            schedules = job['Value'].split(',')
            print(f"[DEBUG] Split schedules: {schedules}")
            
            for schedule in schedules:
                try:
                    print(f"\n[DEBUG] Processing schedule: {schedule}")
                    
                    # First, split on the hyphen to separate the time range
                    time_range_parts = schedule.strip().split('-')
                    print(f"[DEBUG] Time range parts: {time_range_parts}")
                    
                    if len(time_range_parts) != 2:
                        print(f"[DEBUG] Invalid time range format")
                        return ResponseObject(False, f"Invalid time range format: {schedule}")
                    
                    # Get the day from the first part (before the first colon)
                    start_parts = time_range_parts[0].split(':', 1)
                    print(f"[DEBUG] Start parts: {start_parts}")
                    
                    if len(start_parts) != 2:
                        print(f"[DEBUG] Invalid start time format")
                        return ResponseObject(False, f"Invalid start time format: {time_range_parts[0]}")
                    
                    day = start_parts[0]
                    start_time = ':'.join(start_parts[1].split(':')[:2])  # Take only HH:MM
                    end_time = ':'.join(time_range_parts[1].split(':')[:2])  # Take only HH:MM
                    
                    print(f"[DEBUG] Parsed values - Day: {day}, Start: {start_time}, End: {end_time}")
                    
                    # Validate day
                    try:
                        day_num = int(day)
                        print(f"[DEBUG] Day number: {day_num}")
                        if not (0 <= day_num <= 6):
                            print(f"[DEBUG] Invalid day number: {day_num}")
                            return ResponseObject(False, "Weekly schedule day must be between 0 (Monday) and 6 (Sunday)")
                    except ValueError as e:
                        print(f"[DEBUG] Day number conversion error: {e}")
                        return ResponseObject(False, f"Invalid day number: {day}")
                    
                    # Validate time format (HH:MM)
                    try:
                        print(f"[DEBUG] Attempting to parse times - Start: {start_time}, End: {end_time}")
                        start_dt = datetime.strptime(start_time, '%H:%M')
                        end_dt = datetime.strptime(end_time, '%H:%M')
                        print(f"[DEBUG] Parsed times successfully - Start: {start_dt}, End: {end_dt}")
                        
                        # Validate time range
                        if start_dt >= end_dt:
                            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                            print(f"[DEBUG] Invalid time range: {start_dt} >= {end_dt}")
                            return ResponseObject(False, f"Invalid time range for {day_names[day_num]}: end time must be after start time")
                            
                    except ValueError as e:
                        print(f"[DEBUG] Time parsing error: {e}")
                        return ResponseObject(False, f"Time must be in HH:MM format: {start_time} or {end_time}")
                    
                except Exception as e:
                    print(f"[DEBUG] Schedule processing error: {str(e)}")
                    return ResponseObject(False, f"Invalid schedule format: {str(e)}")
                
            # Validate no duplicate days
            days = [s.split('-')[0].split(':', 1)[0].strip() for s in schedules]
            print(f"[DEBUG] Checking for duplicate days: {days}")
            if len(days) != len(set(days)):
                print(f"[DEBUG] Found duplicate days")
                return ResponseObject(False, "Duplicate days are not allowed")
                
        except Exception as e:
            print(f"[DEBUG] Top-level error: {str(e)}")
            return ResponseObject(False, f"Invalid weekly schedule format: {str(e)}")

    print("[DEBUG] Validation completed successfully")
    if "Peer" not in job.keys() or "Configuration" not in job.keys():
        return ResponseObject(False, "Please specify peer and configuration")
    configuration = Configurations.get(job['Configuration'])
    f, fp = configuration.searchPeer(job['Peer'])
    if not f:
        return ResponseObject(False, "Peer does not exist")

    s, p = AllPeerJobs.saveJob(PeerJob(
        job['JobID'], job['Configuration'], job['Peer'], job['Field'], job['Operator'], job['Value'],
        job['CreationDate'], job['ExpireDate'], job['Action']))
    if s:
        return ResponseObject(s, data=p)
    return ResponseObject(s, message=p)

@peer_jobs_blueprint.post('/deletePeerScheduleJob/')
def API_deletePeerScheduleJob():
    data = request.json
    if "Job" not in data.keys():
        return ResponseObject(False, "Please specify job")
    job: dict = data['Job']
    if "Peer" not in job.keys() or "Configuration" not in job.keys():
        return ResponseObject(False, "Please specify peer and configuration")
    configuration = Configurations.get(job['Configuration'])
    f, fp = configuration.searchPeer(job['Peer'])
    if not f:
        return ResponseObject(False, "Peer does not exist")

    s, p = AllPeerJobs.deleteJob(PeerJob(
        job['JobID'], job['Configuration'], job['Peer'], job['Field'], job['Operator'], job['Value'],
        job['CreationDate'], job['ExpireDate'], job['Action']))
    if s:
        return ResponseObject(s, data=p)
    return ResponseObject(s, message=p)

@peer_jobs_blueprint.get('/getPeerScheduleJobLogs/<configName>')
def API_getPeerScheduleJobLogs(configName):
    if configName not in Configurations.keys():
        return ResponseObject(False, "Configuration does not exist")
    data = request.args.get("requestAll")
    requestAll = False
    if data is not None and data == "true":
        requestAll = True
    return ResponseObject(data=JobLogger.getLogs(requestAll, configName))


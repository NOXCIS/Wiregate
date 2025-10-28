"""
FastAPI Peer Jobs Router
Migrated from peer_jobs_api.py Flask blueprint
"""
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from typing import Dict, Any

from ..models.responses import StandardResponse
from ..models.requests import JobCreate
from ..modules.Jobs import JobLogger, PeerJob, AllPeerJobs
from ..modules.Core import Configurations
from ..modules.Security.fastapi_dependencies import require_authentication, get_async_db

logger = logging.getLogger('wiregate')

# Create router
router = APIRouter()


@router.post('/savePeerScheduleJob/', response_model=StandardResponse)
async def save_peer_schedule_job(
    job_request: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication),
    async_db = Depends(get_async_db)
):
    """Save or update a peer schedule job"""
    if "Job" not in job_request:
        return StandardResponse(
            status=False,
            message="Please specify job"
        )
    
    job_dict: dict = job_request['Job']
    logger.debug(f"Received job data: {json.dumps(job_dict, indent=2)}")
    
    # Validate required fields
    required_fields = ['Field', 'Action', 'Value']
    for field in required_fields:
        if field not in job_dict or not job_dict[field]:
            return StandardResponse(
                status=False,
                message=f"Missing required field: {field}"
            )
    
    # Validate Field values
    valid_fields = ['total_receive', 'total_sent', 'total_data', 'date', 'weekly']
    if job_dict['Field'] not in valid_fields:
        return StandardResponse(
            status=False,
            message=f"Invalid field: {job_dict['Field']}. Must be one of: {', '.join(valid_fields)}"
        )
    
    # Validate Action values
    valid_actions = ['allow', 'restrict', 'delete', 'rate_limit']
    if job_dict['Action'] not in valid_actions:
        return StandardResponse(
            status=False,
            message=f"Invalid action: {job_dict['Action']}. Must be one of: {', '.join(valid_actions)}"
        )
    
    # Validate Operator for non-weekly fields
    if job_dict['Field'] != 'weekly':
        if 'Operator' not in job_dict or not job_dict['Operator']:
            return StandardResponse(
                status=False,
                message="Operator is required for non-weekly fields"
            )
        valid_operators = ['eq', 'neq', 'lgt', 'lst']
        if job_dict['Operator'] not in valid_operators:
            return StandardResponse(
                status=False,
                message=f"Invalid operator: {job_dict['Operator']}. Must be one of: {', '.join(valid_operators)}"
            )
    
    # Validate rate limit action
    if job_dict['Action'] == 'rate_limit':
        try:
            rates = json.loads(job_dict.get('Value', '{}'))
            if not isinstance(rates, dict) or 'upload_rate' not in rates or 'download_rate' not in rates:
                return StandardResponse(
                    status=False,
                    message="Invalid rate limit format. Must specify upload_rate and download_rate"
                )
            
            # Validate rate values are positive numbers
            if not isinstance(rates['upload_rate'], (int, float)) or rates['upload_rate'] < 0:
                return StandardResponse(
                    status=False,
                    message="Upload rate must be a positive number"
                )
            if not isinstance(rates['download_rate'], (int, float)) or rates['download_rate'] < 0:
                return StandardResponse(
                    status=False,
                    message="Download rate must be a positive number"
                )
                
        except json.JSONDecodeError:
            return StandardResponse(
                status=False,
                message="Invalid rate limit format"
            )
    
    # Validate weekly schedule format
    if job_dict['Field'] == 'weekly':
        logger.debug(f"Processing weekly schedule. Value: {job_dict['Value']}")
        try:
            if not job_dict['Value']:
                return StandardResponse(
                    status=False,
                    message="Weekly schedule cannot be empty"
                )
                
            schedules = job_dict['Value'].split(',')
            logger.debug(f"Split schedules: {schedules}")
            
            for schedule in schedules:
                try:
                    logger.debug(f"Processing schedule: {schedule}")
                    
                    # Split on hyphen to separate time range
                    time_range_parts = schedule.strip().split('-')
                    logger.debug(f"Time range parts: {time_range_parts}")
                    
                    if len(time_range_parts) != 2:
                        logger.debug(f"Invalid time range format")
                        return StandardResponse(
                            status=False,
                            message=f"Invalid time range format: {schedule}"
                        )
                    
                    # Get day from first part
                    start_parts = time_range_parts[0].split(':', 1)
                    logger.debug(f"Start parts: {start_parts}")
                    
                    if len(start_parts) != 2:
                        logger.debug(f"Invalid start time format")
                        return StandardResponse(
                            status=False,
                            message=f"Invalid start time format: {time_range_parts[0]}"
                        )
                    
                    day = start_parts[0]
                    start_time = ':'.join(start_parts[1].split(':')[:2])
                    end_time = ':'.join(time_range_parts[1].split(':')[:2])
                    
                    logger.debug(f"Parsed values - Day: {day}, Start: {start_time}, End: {end_time}")
                    
                    # Validate day
                    try:
                        day_num = int(day)
                        logger.debug(f"Day number: {day_num}")
                        if not (0 <= day_num <= 6):
                            logger.debug(f"Invalid day number: {day_num}")
                            return StandardResponse(
                                status=False,
                                message="Weekly schedule day must be between 0 (Monday) and 6 (Sunday)"
                            )
                    except ValueError as e:
                        logger.debug(f"Day number conversion error: {e}")
                        return StandardResponse(
                            status=False,
                            message=f"Invalid day number: {day}"
                        )
                    
                    # Validate time format
                    try:
                        logger.debug(f"Attempting to parse times - Start: {start_time}, End: {end_time}")
                        start_dt = datetime.strptime(start_time, '%H:%M')
                        end_dt = datetime.strptime(end_time, '%H:%M')
                        logger.debug(f"Parsed times successfully - Start: {start_dt}, End: {end_dt}")
                        
                        # Validate time range
                        if start_dt >= end_dt:
                            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                            logger.debug(f"Invalid time range: {start_dt} >= {end_dt}")
                            return StandardResponse(
                                status=False,
                                message=f"Invalid time range for {day_names[day_num]}: end time must be after start time"
                            )
                            
                    except ValueError as e:
                        logger.debug(f"Time parsing error: {e}")
                        return StandardResponse(
                            status=False,
                            message=f"Time must be in HH:MM format: {start_time} or {end_time}"
                        )
                    
                except Exception as e:
                    logger.debug(f"Schedule processing error: {str(e)}")
                    return StandardResponse(
                        status=False,
                        message=f"Invalid schedule format: {str(e)}"
                    )
                
            # Validate no duplicate days
            days = [s.split('-')[0].split(':', 1)[0].strip() for s in schedules]
            logger.debug(f"Checking for duplicate days: {days}")
            if len(days) != len(set(days)):
                logger.debug(f"Found duplicate days")
                return StandardResponse(
                    status=False,
                    message="Duplicate days are not allowed"
                )
                
        except Exception as e:
            logger.debug(f"Top-level error: {str(e)}")
            return StandardResponse(
                status=False,
                message=f"Invalid weekly schedule format: {str(e)}"
            )
    
    logger.debug("Validation completed successfully")
    if "Peer" not in job_dict or "Configuration" not in job_dict:
        return StandardResponse(
            status=False,
            message="Please specify peer and configuration"
        )
    
    configuration = Configurations.get(job_dict['Configuration'])
    if not configuration:
        return StandardResponse(
            status=False,
            message="Configuration does not exist"
        )
    
    f, fp = configuration.searchPeer(job_dict['Peer'])
    if not f:
        return StandardResponse(
            status=False,
            message="Peer does not exist"
        )
    
    s, p = AllPeerJobs.saveJob(PeerJob(
        job_dict.get('JobID'),
        job_dict['Configuration'],
        job_dict['Peer'],
        job_dict['Field'],
        job_dict.get('Operator'),
        job_dict['Value'],
        job_dict.get('CreationDate'),
        job_dict.get('ExpireDate'),
        job_dict['Action']
    ))
    
    if s:
        return StandardResponse(status=True, data=[])
    return StandardResponse(status=False, message=p)


@router.post('/deletePeerScheduleJob/', response_model=StandardResponse)
async def delete_peer_schedule_job(
    job_request: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication),
    async_db = Depends(get_async_db)
):
    """Delete a peer schedule job"""
    if "Job" not in job_request:
        return StandardResponse(
            status=False,
            message="Please specify job"
        )
    
    job_dict: dict = job_request['Job']
    
    if "Peer" not in job_dict or "Configuration" not in job_dict:
        return StandardResponse(
            status=False,
            message="Please specify peer and configuration"
        )
    
    configuration = Configurations.get(job_dict['Configuration'])
    if not configuration:
        return StandardResponse(
            status=False,
            message="Configuration does not exist"
        )
    
    f, fp = configuration.searchPeer(job_dict['Peer'])
    if not f:
        return StandardResponse(
            status=False,
            message="Peer does not exist"
        )
    
    s, p = AllPeerJobs.deleteJob(PeerJob(
        job_dict.get('JobID'),
        job_dict['Configuration'],
        job_dict['Peer'],
        job_dict.get('Field'),
        job_dict.get('Operator'),
        job_dict.get('Value'),
        job_dict.get('CreationDate'),
        job_dict.get('ExpireDate'),
        job_dict.get('Action')
    ))
    
    if s:
        return StandardResponse(status=True, data=[])
    return StandardResponse(status=False, message=p)


@router.get('/getPeerScheduleJobLogs/{configName}', response_model=StandardResponse)
async def get_peer_schedule_job_logs(
    configName: str,
    requestAll: str = Query(default="false", description="Request all logs"),
    user: Dict[str, Any] = Depends(require_authentication),
    async_db = Depends(get_async_db)
):
    """Get peer schedule job logs for a configuration"""
    if configName not in Configurations.keys():
        return StandardResponse(
            status=False,
            message="Configuration does not exist"
        )
    
    request_all = requestAll == "true"
    logs = JobLogger.getLogs(request_all, configName)
    
    return StandardResponse(
        status=True,
        data=[log.to_dict() for log in logs]
    )


from flask import (Blueprint, request)
import logging

from ..modules.App import (
    ResponseObject
)

from ..modules.Core import (
    Configurations
)

data_chart_blueprint = Blueprint('data_charts', __name__)

@data_chart_blueprint.route('/getConfigurationRealtimeTraffic', methods=['GET'])
def API_getConfigurationRealtimeTraffic():
    configurationName = request.args.get('configurationName')
    print(f"API_getConfigurationRealtimeTraffic: Requested for configuration '{configurationName}'")
    
    if configurationName is None or configurationName not in Configurations.keys():
        print(f"API_getConfigurationRealtimeTraffic: Configuration '{configurationName}' does not exist")
        return ResponseObject(False, "Configuration does not exist")
    
    traffic_data = Configurations[configurationName].getRealtimeTrafficUsage()
    print(f"API_getConfigurationRealtimeTraffic: Retrieved traffic data for '{configurationName}': {traffic_data}")
    
    return ResponseObject(data=traffic_data)
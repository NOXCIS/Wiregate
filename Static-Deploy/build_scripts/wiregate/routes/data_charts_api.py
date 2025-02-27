from flask import (Blueprint, request)

from ..modules.shared import (
    ResponseObject
)

from ..modules.Core import (
    Configurations
)

data_chart_blueprint = Blueprint('data_charts', __name__)

@data_chart_blueprint.route('/getConfigurationRealtimeTraffic', methods=['GET'])
def API_getConfigurationRealtimeTraffic():
    configurationName = request.args.get('configurationName')
    if configurationName is None or configurationName not in Configurations.keys():
        return ResponseObject(False, "Configuration does not exist")
    return ResponseObject(data=Configurations[configurationName].getRealtimeTrafficUsage())
from flask import Blueprint, request
from wiregate.modules.Locale.Locale import Locale
from wiregate.modules.shared import ResponseObject

locale_blueprint = Blueprint('locale', __name__)
locale_instance = Locale()





@locale_blueprint.get('/locale')
def API_Locale_CurrentLang():
    return ResponseObject(data=locale_instance.getLanguage())


@locale_blueprint.get('/locale/available')
def API_Locale_Available():
    return ResponseObject(data=locale_instance.activeLanguages)


@locale_blueprint.post('/locale/update')
def API_Locale_Update():
    data = request.get_json()
    if 'lang_id' not in data.keys():
        return ResponseObject(False, "Please specify a lang_id")
    locale_instance.updateLanguage(data['lang_id'])
    return ResponseObject(data=locale_instance.getLanguage())

import ipaddress, subprocess, datetime, os, util
from datetime import datetime, timedelta
from flask import jsonify
from util import *
import configparser

notEnoughParameter = {"status": False, "reason": "Please provide all required parameters."}
good = {"status": True, "reason": ""}

def ret(status=True, reason="", data=""):
    return {"status": status, "reason": reason, "data": data}





class managePeer:
    def getPeerDataUsage(self, data, cur):
        now = datetime.now()
        now_string = now.strftime("%d/%m/%Y %H:%M:%S")
        interval = {
            "30min": now - timedelta(hours=0, minutes=30),
             "1h": now - timedelta(hours=1, minutes=0), 
             "6h": now - timedelta(hours=6, minutes=0), 
             "24h": now - timedelta(hours=24, minutes=0), 
             "all": ""
        }
        if data['interval'] not in interval.keys():
            return {"status": False, "reason": "Invalid interval."}
        intv = ""
        if data['interval'] != "all":
            t = interval[data['interval']].strftime("%d/%m/%Y %H:%M:%S")
            intv = f" AND time >= '{t}'"
        timeData = cur.execute(f"SELECT total_receive, total_sent, time FROM wg0_transfer WHERE id='{data['peerID']}' {intv} ORDER BY time DESC;")
        chartData = []
        for i in timeData:
            chartData.append({
                "total_receive": i[0],
                "total_sent": i[1],
                "time": i[2]
            })
        return {"status": True, "reason": "", "data": chartData}




class settings:
    def setTheme(self, theme, config, setConfig):
        themes = ['light', 'dark']
        if theme not in themes: 
            return ret(status=False, reason="Theme does not exist")
        config['Server']['dashboard_theme'] = theme
        setConfig(config)
        return ret()
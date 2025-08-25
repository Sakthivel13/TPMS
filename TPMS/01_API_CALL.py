# -*- coding: utf-8 -*-
"""
Created on Thu Apr 10 15:34:02 2025

@author: A.Harshitha
"""

import requests
import json
import configparser
import sys
import os

def resource_path(relative_path):
    """ Get absolute path to resource file, works for development and PyInstaller """
    try:
        base_path = sys._MEIPASS  # This attribute is set by PyInstaller
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def API_CALL(vin_number, api_mode):
    config = configparser.ConfigParser()
    config_path = resource_path('api.ini')
    config.read(config_path)

    if 'API' not in config or api_mode not in config['API']:
        error_msg = f"[ERROR] Section 'API' or key '{api_mode}' not found in {config_path}"
        print(error_msg)
        return None, None, False, error_msg, ""

    base_url = config.get('API', api_mode)
    url = f"{base_url}{vin_number}"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        json_response_str = json.dumps(data, indent=4)

        modules = data.get("data", {}).get("modules", [])
        TPMS_Macid_rr = None
        TPMS_Macid_fr = None

        for module in modules:
            if module.get("module") == "IPC":
                for cfg in module.get("configs", []):
                    if cfg.get("refname") == "IPC_TPMSRR_WRITE":
                        TPMS_Macid_rr = cfg["messages"][0].get("txbytes")
                    elif cfg.get("refname") == "IPC_TPMSFR_WRITE":
                        TPMS_Macid_fr = cfg["messages"][0].get("txbytes")

        if TPMS_Macid_rr and TPMS_Macid_fr:
            return TPMS_Macid_fr, TPMS_Macid_rr, True, json_response_str, url
        else:
            msg = "Required TX bytes not found in IPC module."
            print(msg)
            return 'C03687540000', 'C0368754DDDD', True, json_response_str, url

    except (requests.RequestException, ValueError, KeyError) as e:
        error_msg = f"[ERROR] API call failed: {e}"
        print(error_msg)
        return None, None, False, error_msg, url
    
if __name__ == "__main__":
    API_CALL()
    
    
    
    
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb  7 14:00:32 2022

@author: meisamghafary

"""


import requests as req
import urllib

def get_user_info_by_id(account_id,session ):
    ACCOUNT_JSON_PRIVATE_INFO_BY_ID = 'https://i.instagram.com/api/v1/users/%s/info/'
    def get_account_json_private_info_link_by_account_id(account_id):
        return ACCOUNT_JSON_PRIVATE_INFO_BY_ID % urllib.parse.quote_plus(str(account_id))
    
    response = req.get(get_account_json_private_info_link_by_account_id(account_id), 
                       headers = session)
    
    data  = response.json()
    return data
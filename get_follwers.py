#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 22 21:51:00 2022

@author: meisamghafary
"""

''''' Data Entry'''
### please enter the page name and give an address for saving data ####
page_name = 'Aliazimiofficial'
path = '/Users/meisamghafary/Desktop/Squad/Scrap_instagram'


pass_ = 'oiuoiuo989'
user = 'meisamlg2021'
user1 = 'shomaei12'
user2 = 'meisam9229'
user3 = 'meisamghafarilan'
user4 = 'meisam.ghafar.g'
u5 = 'meisamlkj'
u6= 'meisamscrap5'
u7 = 'meisam_scrap'
u8 = 'Meisam4_Scrap'
u9 = 'meisam_scarp5'
u10 = 'meisamscrap6'
u11 = 'meisamscrap7'
u12 = 'meisamscrap8'

users=[(u8, pass_), (u10, pass_), (user, pass_), (user2, pass_)]

import os
mak_path = path + '/Data_{}'.format(page_name)
if os.path.isdir(mak_path)== False:
    os.mkdir(mak_path)

path_data = path + '/Data_{}'.format(page_name)
path_followers = path_data+'/followers_info.csv'
os.chdir(path)


from igramscraper.instagram import Instagram
import time
import pandas as pd
import numpy as np
import random
import warnings
warnings.filterwarnings('ignore')



if not 'total_connect'  in globals():
    total_connect = []
    cn = 0
    
    for i in users:
        cn += 1
        globals()['instagram_%s' % cn] = Instagram(0)
        inst = globals()['instagram_%s' % cn]
        u, p = i
        print(u)
        inst.with_credentials(u, p)
        inst.login()
        print(inst.get_account(f'{page_name}'))
        total_connect.append(inst)


acc = inst.get_account(f'{page_name}')
page_ = acc.__dict__


pages = None
has_next = True
account_info = {}
i=0

print('Accounts info are downloading ...')

while has_next:
    i+=1
    time.sleep(np.random.randint(2))
    instagram = random.choice(total_connect)
    try:
        comm, has_next = instagram.get_followers(account_id = page_['identifier'],count=  50, end_cursor=pages)
        pages = comm['next_page']
        accounts = comm['accounts']
        c = [cc.__dict__ for cc in accounts]
        account_info[i]  = pd.DataFrame(c).rename(columns = {'identifier':"user_ID"})
    except Exception as e:
        print(f'\n {e}')
        continue


pd.concat(account_info).to_csv(path_followers, index= False)








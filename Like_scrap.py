
''''' Data Entry'''

### please enter the page name and give an address for saving data ####
page_name = 'Aliazimiofficial'
path = '/Users/meisamghafary/Desktop/Squad/Scrap_instagram'
num_posts = None


user = 'meisamlg2021'
user1 = 'shomaei12'
pass_ = 'Parsian6767'
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

users=[(u10, pass_),(u6, pass_)]

""" This part is executed automatically"""

import os
if os.path.isdir(path)==False:
    os.mkdir(path + '/Data_{}'.format(page_name))

os.chdir(path)

path_data = path + '/Data_{}'.format(page_name)
path_save_likes = path_data+'/likes.csv'
path_page_id = path_data+'/max_ID_likes.csv'
path_page_info = path_data+'/page_info.csv'
path_user_info = path_data+'/user_info.csv'

from igramscraper.instagram import Instagram
from tqdm import tqdm
import pandas as pd
import numpy as np
import random
import time 
from datetime import datetime


def save_dln(result, pages):
    all_likes = pd.concat(result).reset_index().drop(['level_1'], 1)
    all_likes['scraping_time']=datetime.now()
    all_likes.columns = ['short_code', 'user_ID','username','full_name','is_verified' ,'scraping_time']
    all_likes.to_csv(path_save_likes)
    pd.DataFrame(pages, index = ['max_id']).T.to_csv(path_page_id)


total_connect = []
cn = 0

if not 'total_connect'  in globals():
    
    for i in users:
        cn += 1
        globals()['instagram_%s' % cn] = Instagram(1)
        inst = globals()['instagram_%s' % cn]
        u, p = i
        print(u)
        inst.with_credentials(u, p)
        inst.login()
        print(inst.get_account(page_name))
        total_connect.append(inst)


acc = inst.get_account(page_name)
page_ = acc.__dict__
num_of_posts = np.where(num_posts!=None ,num_posts, page_['media_count'])


print(f'\n **** Toal number of media is {num_of_posts} **** \n')
print(f'\n **** Info Pages are downloading .... please wait ...**** \n')

media = total_connect[0].get_medias(page_name, num_of_posts)
c = [cc.__dict__ for cc in media]
df = pd.DataFrame(c)
df.to_csv(path_page_info)

all_lik  = df.likes_count.sum()
print(f'\n **** Number of likes is {all_lik} **** \n')


short_codes = df.sort_values('likes_count')['short_code'].to_list()
pages = {k: None for k in short_codes}
likes_all_id = pd.DataFrame(columns= ['id', 'username', 'full_name', 'is_verified'])
first_time = time.time()
likes = {k: likes_all_id for k in short_codes}


while len(short_codes) > 0:    
    for i in tqdm(short_codes):
        if time.time() - first_time >300:
            save_dln(likes, pages)
            first_time = time.time()
        instagram = random.choice(total_connect)
        try:
            lik, max_id, next_page = instagram.get_media_likes_by_code(i, 50, max_id=pages[i])
        except Exception as e:
            print(f'\n {e} \n')
            continue
            
        likes[i] = pd.concat([lik[['id', 'username', 'full_name', 'is_verified']], likes[i]], 0)
        if next_page:
            pages[i] = max_id
        else:
            short_codes.remove(i)


save_dln(likes, pages)


# ### Get Likers Informations


# standart_properties = [
#     'username',
#     'full_name',
#     'biography',
#     'external_url',
#     'is_private',
#     'is_verified',
#     'is_business',
#     'public_email',
#     'public_phone_number',
#     'public_phone_country_code',
#     'media_count',
#     'follower_count',
#     'following_count',
#     'can_be_reported_as_fraud', 
#     'longitude', 
#     'latitude'
#     ]

# data = pd.read_csv(path_save_likes)
# users_likes = data.user_ID.drop_duplicates().to_list()

# total_connect = []
# for i in users:
#     cn += 1
#     globals()['instagram_%s' % cn] = Instagram(1)
#     inst = globals()['instagram_%s' % cn]
#     u, p = i
#     print(u)
#     inst.with_credentials(u, p)
#     seission = inst.login()
#     total_connect.append(seission)

# info_users = {k: None for k in users_likes}

# from igramscraper.get_info_json import get_user_info_by_id

# for u in tqdm(users_likes):
#     instagram = random.choice(total_connect)
#     info = get_user_info_by_id(u, instagram)
#     json_string = json.dumps(info)
    
#     with open(path_data+f'/{u}.json', 'w') as outfile:
#         outfile.write(json_string)
        
#     info = info['user']
#     all_= info.keys()
#     nec_info =  {k: None for k in standart_properties}
#     for k in standart_properties:
#         try:
#             nec_info[k] = info[k]
#         except:
#             nec_info[k] = None
#     info_users[u] = pd.DataFrame(nec_info, index= ['info']).T



# all_users = pd.concat(info_users).reset_index(col_level=0)
# all_users.columns = ['user_ID','level_1' ,'info_user']
# all_users = all_users.pivot('user_ID', columns= 'level_1', values='info_user')


# all_users.to_csv(path_user_info, index_label= False)

# pd.read_csv(path_user_info)


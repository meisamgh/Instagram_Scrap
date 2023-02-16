
''''' Data Entry'''
### please enter the page name and give an address for saving data ####
page_name = 'Aliazimiofficial'
path = '/Users/meisamghafary/Desktop/Squad/Scrap_instagram'
num_posts = None

pass_ = 'Parsian46321'
user = 'meisamlg2021'
user1 = 'shomaei12'
pass_ = 'Parsian46321'
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


""" This part is executed automatically"""
import os
mak_path = path + '/Data_{}'.format(page_name)
if os.path.isdir(mak_path)== False:
    os.mkdir(mak_path)

path_data = path + '/Data_{}'.format(page_name)
path_save_comment = path_data+'/comments.csv'
path_page_id = path_data+'/max_ID_comments.csv'
path_replay = path_data+'/replay.csv'
path_user_info = path_data+'/user_inof.csv'
page_info = path_data +'/page_info.csv'

os.chdir(path)

from igramscraper.instagram import Instagram

import time
from tqdm import tqdm
import pandas as pd
import numpy as np
import random
import datetime
import warnings
warnings.filterwarnings('ignore')

def save_dln(comments,replay, pages):
    comments.reset_index(inplace = True)
    comments.rename(columns = {'identifier':'id_comments',
                               'level_0':'short_codes'}, 
                    inplace = True)

    c = [cc.__dict__ for cc in comments.owner]
    df = pd.DataFrame(c)
    comments = pd.concat([df, comments], 1)
    comments.rename(columns = {'identifier':'user_ID'}, 
                    inplace = True)
    
    comments['scraping_time'] = datetime.datetime.now()
    comments.to_csv(path_save_comment, index=False)
    pd.DataFrame(pages, index = ['max_id']).T.to_csv(path_page_id)
    replay.to_csv(path_replay)


def data_frame_comments(comment_all):
    result_cmm = {}
    for k,v in comment_all.items():
        c = [cc.__dict__ for cc in v]
        result_cmm[k]= pd.DataFrame(c)
    comments = pd.concat(result_cmm)    
    return comments



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


acc = total_connect[0].get_account(page_name)
page_ = acc.__dict__
num_of_posts = np.where(num_posts!=None ,num_posts, page_['media_count'])


print(f"\n **** Toal number of media is {num_of_posts} **** ")
print('\n **** Info Pages are downloading .... please wait ...****')


media = total_connect[0].get_medias(page_name, num_of_posts)
c = [cc.__dict__ for cc in media]
df = pd.DataFrame(c)
df.to_csv(page_info)

all_lik  = df.comments_count.sum()
print(f'\n **** Number of comments is {all_lik} ****')
print( f'\n Elapsed time is {round(all_lik/(20*3600),2)} hours')

if round(all_lik/(20*3600),2)>24:
   print( f'\n Elapsed time is {round(all_lik/(20*3600)/24,2)} days')


short_codes = df.short_code.to_list()

cnt = 0
likes_all = {}
pages = {k: None for k in short_codes}
comment_all = {k: [] for k in short_codes}


all_replay = pd.DataFrame()
first_time = time.time()


while len(short_codes) > 0:
#    print(f'start Time is {datetime.datetime.now()}')
    for i in tqdm(short_codes):
        if time.time() - first_time >300:
            comm  = data_frame_comments(comment_all)
            save_dln(comm, all_replay, pages)
            first_time = time.time()
        instagram = random.choice(total_connect)
        try:
            comm, max_id, next_page, replay = instagram.get_media_comments_by_code(i, 50, max_id=pages[i])
            
        except Exception as e:
            print(f'\n {e}')
            continue         

        comment_all[i] = [*comment_all[i], *comm]
        all_replay = pd.concat([all_replay, replay],0)

        if ((next_page) | (len(comm)==0)):
            pages[i] = max_id
        else:
            short_codes.remove(i)


comm  = data_frame_comments(comment_all)
save_dln(comm, all_replay, pages)


c = [cc.__dict__ for cc in comm.owner]
df = pd.DataFrame(c)




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
#     'latitude']

# data = pd.read_csv(path_save_comment)
# users_likes = data.id_commentor.drop_duplicates().to_list()


# total_connect = []
# if 'total_connect' not in globals():
#     total_connect = []
#     cn = 0
#     for i in users:
#         cn += 1
#         globals()['instagram_%s' % cn] = Instagram(0)
#         inst = globals()['instagram_%s' % cn]
#         u, p = i
#         print(u)
#         inst.with_credentials(u, p)
#         inst.login()
#         print(inst.get_account(f'{page_name}'))
#         total_connect.append(inst)


# info_users = {k: None for k in users_likes}
# info_users_jason = {k: None for k in users_likes}
# from igramscraper.get_info_json import get_user_info_by_id


# for u in tqdm(users_likes):
#     print(u)
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




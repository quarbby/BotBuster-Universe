import os, joblib
import utils_model_helper
import json
import pandas as pd
import numpy as np

# Global variables
desc_model = None
username_model = None
screenname_model = None
posts_model = None
posts_metadata_model = None
user_metadata_model = None

folder_to_run = None

out_fh = None

def read_models():
    try:
        models_folder = "models"
        global desc_model, username_model, screenname_model, posts_model, posts_metadata_model, user_metadata_model
        
        desc_model = joblib.load(os.path.join(models_folder, 'description.pkl'))
        username_model = joblib.load(os.path.join(models_folder, 'user_name.pkl'))
        screenname_model = joblib.load(os.path.join(models_folder, 'screen_name.pkl'))
        posts_model = joblib.load(os.path.join(models_folder, 'posts.pkl'))
        posts_metadata_model = joblib.load(os.path.join(models_folder, 'posts_metadata.pkl'))
        user_metadata_model = joblib.load(os.path.join(models_folder, 'user_metadata.pkl'))
        return 1
    
    except:
        return 0

def check_known_expert(username, screenname, description, is_verified):
    if is_verified == True:
        return 'human'
    
    if username != None and username != '':
        username = username.lower()
        if 'bot' in username:
            return 'bot'
        
    if description is not None and description != '':
        description = description.lower()
        if 'bot' in description:
            return 'bot'
        
    if screenname is not None and screenname != '':
        screenname = screenname.lower()
        if 'bot' in screenname:
            return 'bot'
    
    return None

# Helper functions to get probabilities of each type
def get_description_prob(description):
    if description == None or description == '':
        return None
    
    description = description.lower()
    
    desc_arr = [{'description': description}]
    df = pd.DataFrame(desc_arr)
    df['description_cleaned'] = df['description'].apply(utils_model_helper.preprocess_text)
    df_test = df[['description_cleaned']]
    predictions = desc_model.predict_proba(df_test)
    
    return predictions

def get_username_prob(username):
    if username == None or username == '':
        return None
    
    username = username.lower()
    
    username_arr = [{'user_name': username}]
    df = pd.DataFrame(username_arr)
    df = utils_model_helper.transform_df(df, 'user_name')
    df_test = df[utils_model_helper.username_cols]
    predictions = username_model.predict_proba(df_test)
    return predictions

def get_screenname_prob(screenname):   
    if screenname == None or screenname == '':
        return None
    
    screenname = screenname.lower()
    
    screenname_arr = [{'screen_name': screenname}]
    df = pd.DataFrame(screenname_arr)
    df = utils_model_helper.transform_df(df, 'screen_name')
    df_test = df[utils_model_helper.screenname_cols]
    predictions = screenname_model.predict_proba(df_test)
    return predictions

def get_posts_prob(df):
    df_text = df[['text_cleaned']]
    post_text_prob = posts_model.predict_proba(df_text)
        
    df_posts_metadata = df[utils_model_helper.posts_data_cols]
    df_posts_metadata = df_posts_metadata[(df_posts_metadata['post_like_count'] != -1) & (df_posts_metadata['post_retweet_count'] != -1) ]

    if len(df_posts_metadata) > 0:
        post_metadata_prob = posts_metadata_model.predict_proba(df_posts_metadata)
        overall_pred = (post_text_prob + post_metadata_prob)/2

    else:
        overall_pred = post_text_prob
    
    return overall_pred

def get_usermetadata_prob(df):    
    df = df.fillna(-1)
    df_temp = df[(df['followers_count'] == -1) & (df['listed_count'] == -1) & \
                        (df['protected'] == -1) & (df['verified'] == -1) & \
                        (df['following_count'] == -1) & (df['like_count'] == -1) ]
    
    cond = df['userid'].isin(df_temp['userid'])
    df_temp_final = df.drop(df[cond].index)
    
    if len(df_temp_final) == 0:
        print('No metadata')
        return None
    
    df_test = df_temp_final[utils_model_helper.usermetadata_cols]
    predictions = user_metadata_model.predict_proba(df_test)
    return predictions

def compute_botbuster_prob(out_fh, userid, username, screenname, description, is_verified, df_posts, df_usermetadata):
    known_data_expert = check_known_expert(username, screenname, description, is_verified) 
    if known_data_expert is not None:
        if known_data_expert == 'bot':
            out_fh.write(f'{userid},0,1,True\n')
            
            return
        elif known_data_expert == 'human':
            out_fh.write(f'{userid},1,0,False\n')
            
            return
                            
    prob_arr = [0, 0]
    count = 0
            
    username_prob = get_username_prob(username)
    if username_prob is not None:
        prob_arr += username_prob[0]
        count += 1   
                
    screenname_prob = get_screenname_prob(screenname)
    if screenname_prob is not None:
        prob_arr += screenname_prob[0]
        count += 1

    description_prob = get_description_prob(description)
    if description_prob is not None:
        prob_arr += description_prob[0]
        count += 1

    if df_posts is not None:
        posts_prob = get_posts_prob(df_posts)
        if posts_prob is not None:
            prob_arr += posts_prob[0]
            count += 1

    if df_usermetadata is not None:
        usermetadata_prob = get_usermetadata_prob(df_usermetadata)
        if usermetadata_prob is not None:
            prob_arr += usermetadata_prob[0]
            count += 1
                
    #print(prob_arr)
    prob_arr_div = prob_arr / count

    bot_prob = prob_arr_div[0]
    human_prob = prob_arr_div[1]

    overall_bot_prob = max(prob_arr_div)
    max_index = np.where(prob_arr_div == overall_bot_prob)[0][0]

    botornot = False
    if max_index == 0:
        botornot = True
    elif max_index == 1:
        botornot = False
    
    out_fh.write(f'{userid},{human_prob},{bot_prob},{botornot}\n')

    return

def get_posts_df_v1(line_json):
    if line_json['full_text'] == '':
        return None
    
    text_cleaned = utils_model_helper.preprocess_text(line_json['full_text'])
    if text_cleaned == '':
        return None
    
    user_post_arr = [{'text_cleaned': text_cleaned,
                      'post_like_count': line_json['favorite_count'],
                      'post_retweet_count': line_json['retweet_count'],
                      'post_reply_count': -1,
                      'post_quote_count': -1
    }]
    
    df = pd.DataFrame(user_post_arr)
    return df

def get_posts_df_v2(tweet):
    if tweet['text'] == '' or tweet['text'] == None:
        return None
    
    text_cleaned = utils_model_helper.preprocess_text(tweet['text'])
    if text_cleaned == '':
        return None
    
    user_post_arr = [{'text_cleaned': text_cleaned,
                      'post_like_count': tweet['public_metrics']['like_count'],
                      'post_retweet_count': tweet['public_metrics']['retweet_count'],
                      'post_reply_count': tweet['public_metrics']['reply_count'],
                      'post_quote_count': tweet['public_metrics']['quote_count']
    }]
    
    df = pd.DataFrame(user_post_arr)
    return df

# For user metadata 
def form_usermetadata_twitter_v1(line_json):
    user_metadata_arr = [{'userid': line_json['user']['id_str'],
                          'followers_count': line_json['user']['followers_count'],
                          'following_count': line_json['user']['friends_count'],
                          'listed_count': line_json['user']['listed_count'],
                          'protected': utils_model_helper.convert_true_false_to_binary(line_json['user']['protected']),
                          'verified': utils_model_helper.convert_true_false_to_binary(line_json['user']['verified']),
                          'like_count': line_json['user']['favourites_count'],
                          'tweet_count': line_json['user']['statuses_count']
    }]
    
    df = pd.DataFrame(user_metadata_arr)
    
    return df

def form_usermetadata_twitter_v2(user):
    user_metadata_arr = [{'userid': user['id'],
                          'followers_count': user['public_metrics']['followers_count'],
                          'following_count': user['public_metrics']['following_count'],
                          'listed_count': user['public_metrics']['listed_count'],
                          'protected': utils_model_helper.convert_true_false_to_binary(user['protected']),
                          'verified': utils_model_helper.convert_true_false_to_binary(user['verified']),
                          'like_count': -1,
                          'tweet_count': user['public_metrics']['tweet_count']
    }]
    
    df = pd.DataFrame(user_metadata_arr)
    
    return df

def form_usermetadata_telegram(line_json):
    if line_json['user'] == None:
        user_metadata_arr = [{'userid': -1,
                            'followers_count': -1,
                            'following_count': -1,
                            'listed_count': -1,
                            'protected': -1,
                            'verified': -1,
                            'like_count': -1,
                            'tweet_count': -1
        }]

    else:

        user_metadata_arr = [{'userid': line_json['user']['id'],
                            'followers_count': -1,
                            'following_count': -1,
                            'listed_count': -1,
                            'protected': -1,
                            'verified': utils_model_helper.convert_true_false_to_binary(line_json['user']['bot']),
                            'like_count': line_json['user']['like_sum'],
                            'tweet_count': line_json['user']['message_count']
        }]
    
    df = pd.DataFrame(user_metadata_arr)

    return df

def run_botbuster_twitter_v1(folder_to_run):
    global out_fh

    files_to_run = utils_model_helper.get_files_torun(folder_to_run)

    for file in files_to_run:
        in_filename = os.path.join(folder_to_run, file)
        print(in_filename)

        out_filename = os.path.join(folder_to_run, file + '_bots.json')
        out_fh =  open(out_filename, 'w', encoding='utf-8')
        out_fh.write('userid,humanprobability,botprobability,botornot\n')

        with open(in_filename, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    line_json = json.loads(line)
                    userid = line_json['user']['id_str']
                    username = line_json['user']['name']
                    screenname = line_json['user']['screen_name']
                    description = line_json['user']['description']
                    is_verified = line_json['user']['verified']
                    
                    df_posts = get_posts_df_v1(line_json)
                    df_usermetadata = form_usermetadata_twitter_v1(line_json)
                    
                    compute_botbuster_prob(out_fh, userid, username, screenname, description, is_verified, df_posts, df_usermetadata)
                except:
                    pass

        out_fh.close()

        return 1

def run_botbuster_twitter_v2(folder_to_run):
    global out_fh

    files_to_run = utils_model_helper.get_files_torun(folder_to_run)
    for file in files_to_run:
        in_filename = os.path.join(folder_to_run, file)
        print(in_filename)

        out_filename = os.path.join(folder_to_run, file + '_bots.json')
        out_fh =  open(out_filename, 'w', encoding='utf-8')
        out_fh.write('userid,humanprobability,botprobability,botornot\n')

        with open(in_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

            if data['meta']['result_count'] == 0:
                print('No data in ', in_filename)
                return 0
            
            user_dict = utils_model_helper.user_json_to_dict(data['includes']['users'])
            tweet_data = data['data']
            total_tweets = len(tweet_data)

            for i in range(0, total_tweets):
                tweet = tweet_data[i]
                userid = tweet['author_id']
                user_obj = user_dict[userid]
                
                username = user_obj['username']
                screenname = user_obj['name']
                description = user_obj['description']
                is_verified = user_obj['verified']
                    
                df_posts = get_posts_df_v2(tweet)
                df_usermetadata = form_usermetadata_twitter_v2(user_obj)

                compute_botbuster_prob(out_fh, userid, username, screenname, description, is_verified, df_posts, df_usermetadata)
    
        out_fh.close()

        return 1

def get_posts_df_reddit(post):
    if post['selftext'] == '' or post['selftext'] == None:
        return None
    
    text = post['title'] + post['selftext']
    
    text_cleaned = utils_model_helper.preprocess_text(text)
    if text_cleaned == '':
        return None
    
    user_post_arr = [{'text_cleaned': text_cleaned,
                      'post_like_count': post['upvote_ratio'],
                      'post_retweet_count': post['num_crossposts'],
                      'post_reply_count': post['num_comments'],
                      'post_quote_count': post['num_crossposts']
    }]
    
    df = pd.DataFrame(user_post_arr)
    return df

def run_botbuster_reddit(folder_to_run):
    global out_fh

    files_to_run = utils_model_helper.get_files_torun(folder_to_run)

    for file in files_to_run:
        in_filename = os.path.join(folder_to_run, file)
        print(in_filename)

        out_filename = os.path.join(folder_to_run, file + '_bots.json')
        out_fh =  open(out_filename, 'w', encoding='utf-8')
        out_fh.write('userid,humanprobability,botprobability,botornot\n')

        with open(in_filename, 'r', encoding='utf-8') as f:
            for line in f:
                line_json = json.loads(line)

                userid = line_json['id']
                username = line_json['author_fullname']
                screenname = line_json['author']
                is_verified = None
                description = None
                
                df_posts = get_posts_df_reddit(line_json)
                df_usermetadata = None
                compute_botbuster_prob(out_fh, userid, username, screenname, description, is_verified, df_posts, df_usermetadata)

        out_fh.close()

    return 1

def run_botbuster_instagram(folder_to_run):
    global out_fh

    files_to_run = utils_model_helper.get_files_torun(folder_to_run)

    for file in files_to_run:
        in_filename = os.path.join(folder_to_run, file)
        print(in_filename)

        out_filename = os.path.join(folder_to_run, file + '_bots.json')
        out_fh =  open(out_filename, 'w', encoding='utf-8')
        out_fh.write('userid,humanprobability,botprobability,botornot\n')

        with open(in_filename, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    line_json = json.loads(line)
                    userid = line_json['user_id']
                    username = line_json['username']
                    screenname = line_json['fullname']
                    is_verified = line_json['is_verified']
                    description = line_json['bio']
                    
                    df_posts = None
                    df_usermetadata = None

                    compute_botbuster_prob(out_fh, userid, username, screenname, description, is_verified, df_posts, df_usermetadata)
                except:
                    pass

        out_fh.close()

def get_posts_df_telegram(post):
    text = post['message']

    if post['message'] == '' or post['message'] == None:
        return None
        
    text_cleaned = utils_model_helper.preprocess_text(text)
    if text_cleaned == '':
        return None
    
    if post['forwards'] is not None:
        forwards = post['forwards']
    else: 
        forwards = -1

    user_post_arr = [{'text_cleaned': text_cleaned,
                      'post_like_count': post['up'],
                      'post_retweet_count': forwards,
                      'post_reply_count': -1,
                      'post_quote_count': -1
    }]
    
    df = pd.DataFrame(user_post_arr)
    return df

def run_botbuster_telegram(folder_to_run):
    global out_fh

    files_to_run = utils_model_helper.get_files_torun(folder_to_run)

    for file in files_to_run:
        in_filename = os.path.join(folder_to_run, file)
        print(in_filename)

        out_filename = os.path.join(folder_to_run, file + '_bots.json')
        out_fh =  open(out_filename, 'w', encoding='utf-8')
        out_fh.write('userid,humanprobability,botprobability,botornot\n')

        messages_all = {}
        users_all = {}

        with open(in_filename, 'r', encoding='utf-8') as f:
            for line in f:
                line_json = json.loads(line)

                if line_json['_'] == 'Message': 
                    user = line_json['from_id']['user_id']

                    up = 0
                    down = 0
                    if line_json['reactions'] is not None:
                        for r in line_json['reactions']['results']:
                            if utils_model_helper.reaction_dict[r['reaction']] == 'up':
                                up += r['count']
                            if utils_model_helper.reaction_dict[r['reaction']] == 'down':
                                down += r['count']

                    line_json['up'] = up
                    line_json['down'] = down

                    if user not in messages_all:
                        messages_all[user] = {'msg': []}
                        messages_all[user]['up'] = 0

                    messages_all[user]['up'] += up
                    messages_all[user]['msg'].append(line_json)

                elif line_json['_'] == 'User':
                    user = line_json['id']
                    if user not in users_all:
                        users_all[user] = line_json

        for user, msg_dict in messages_all.items():
            messages_list = msg_dict['msg']
            message_count = len(messages_list)
            like_sum = msg_dict['up']

            user_data = users_all[user]
            if user_data is not None:
                user_data['message_count'] = message_count
                user_data['like_sum'] = like_sum

            for m in messages_list:
                message = {'message': m['message'], 'forwards': m['forwards'], 'up': m['up'], 'down': m['down'], 'id': m['id'], 'user': user_data}
 
                # run probablity model already
                df_posts = get_posts_df_telegram(message)
                df_usermetadata = form_usermetadata_telegram(message)

                userid = message['user']['id']
                username = message['user']['username']
                screenname = message['user']['first_name'] + message['user']['last_name']
                description = ""
                is_verified = message['user']['verified']

                compute_botbuster_prob(out_fh, userid, username, screenname, description, is_verified, df_posts, df_usermetadata)

        out_fh.close()

        return 1
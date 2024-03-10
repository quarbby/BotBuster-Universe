import os, joblib
import json, pickle
import pandas as pd
from sentence_transformers import SentenceTransformer

import utils_model_helper
import botsorter_algo
import botbias_algo

# Global variables
out_fh = None
out_bias_filename = None
username_model = None
posts_model = None
news_model = None 
sentence_model = None
identities_terms = None
authority_terms = None

def read_models():
    try:
        models_folder = "models"
        global username_model, posts_model, news_model, sentence_model, identities_terms, authority_terms

        username_model = joblib.load(os.path.join(models_folder, 'user_name.pkl'))
        posts_model = joblib.load(os.path.join(models_folder, 'posts.pkl'))

        news_model_filename = os.path.join(models_folder, 'news_logregmodel.pkl')
        with open(news_model_filename, 'rb') as f:
            news_model = pickle.load(f)

        sentence_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

        identities_df = pd.read_csv(os.path.join(models_folder, 'identities.csv'))
        identities_terms = identities_df['term'].str.lower().tolist()

        authority_df = pd.read_csv(os.path.join(models_folder, 'authority_identities.csv'))
        authority_terms = authority_df['term'].str.lower().tolist()

        return 1
    except:
        return 0

def check_type_of_bias(data, platform):
    global identities_terms, authority_terms, out_bias_filename, sentence_model

    bias_data = {}
    post_parsed = []

    for userid, post_list in data.items():
        if userid not in bias_data:
            bias_data[userid] = {}

        sentiment_list = []
        for post in post_list:
            postid = post['id']
            if post not in post_parsed:
                bias_data[userid][postid] = {}
                post_parsed.append(postid)

            homophily = botbias_algo.check_homophily(post, platform, identities_terms)
            bias_data[userid][postid]['bias_homophily'] = homophily

            affect, negativity, compound = botbias_algo.check_affect(post, platform)
            bias_data[userid][postid]['bias_affect'] = affect
            bias_data[userid][postid]['bias_negativity'] = negativity
            sentiment_list.append((postid, compound))

            authority = botbias_algo.check_authority(post, platform, authority_terms)
            bias_data[userid][postid]['bias_authority'] = authority

        illusory_truth_postids = botbias_algo.check_illusory_truth(post_list, platform, sentence_model)
        if illusory_truth_postids is not None:
            for illusory_id in illusory_truth_postids:
                bias_data[userid][illusory_id]['bias_illusory_truth_effect'] = True

        availability_postids = botbias_algo.check_availability(post_list, platform)
        if availability_postids is not None:
            for avail_id in availability_postids:
                bias_data[userid][avail_id]['bias_availability'] = True

        confirmation_ids = botbias_algo.check_confirmation(sentiment_list)
        if confirmation_ids is not None:
            for confirm_id in confirmation_ids:
                bias_data[userid][confirm_id]['bias_confirmation'] = True

    bias_concat = []
    for userid, post_list in bias_data.items():
        for postid, post in post_list.items():
            if not 'bias_illusory_truth_effect' in post:
                post['bias_illusory_truth_effect'] = False 
            if not 'bias_availability' in post:
                post['bias_availability'] = False
            if not 'bias_confirmation' in post:
                post['bias_confirmation'] = False

            m = {'userid': userid, 'postid': postid, 'bias_homophily': post['bias_homophily'], 'bias_affect': post['bias_affect'], 'bias_negativity': post['bias_negativity'], 'bias_illusory_truth_effect': post['bias_illusory_truth_effect'], 'bias_availability': post['bias_availability'], 'bias_authority': post['bias_authority'], 'bias_confirmation': post['bias_confirmation']}
            bias_concat.append(m)
    df = pd.DataFrame(bias_concat)
    df.to_csv(out_bias_filename, index=False)

def check_type_of_bot(data, platform, userid):   
    global out_fh, news_model, sentence_model, posts_model

    if len(data) == 0:
        return

    self_declared_bot = botsorter_algo.check_if_self_declared_bot(data, platform)

    news_bot = botsorter_algo.check_if_news_bot(data, platform, news_model)

    bridging_bot = botsorter_algo.check_if_bridging_bot(data, platform)

    amplifier_bot = botsorter_algo.check_if_amplifier_bot(data, platform)

    cyborg = botsorter_algo.check_if_cyborg(data, platform, posts_model)

    content_generation_bot = botsorter_algo.check_if_content_generation_bot(data, platform)

    announcer_bot = botsorter_algo.check_if_announcer_bot(data, platform)

    repeater_bot = botsorter_algo.check_if_repeater_bot(data, platform, sentence_model)

    num_posts = len(data)

    out_fh.write(f'{userid},{num_posts},{self_declared_bot},{news_bot},{bridging_bot},{amplifier_bot},{cyborg},{content_generation_bot},{announcer_bot},{repeater_bot}\n')

def run_botsorter_twitter_v1(folder_to_run):
    global out_fh, out_bias_filename
    
    files_to_run = utils_model_helper.get_files_torun(folder_to_run)
    filtered_files = [file for file in files_to_run if '_bots.json' not in file]
    filtered_files = [file for file in filtered_files if '.tsv' not in file]

    for file in filtered_files:
        in_filename = os.path.join(folder_to_run, file)
        print(in_filename)

        out_filename = os.path.join(folder_to_run, file + '_botssorter.json')
        out_fh =  open(out_filename, 'w', encoding='utf-8')
        out_fh.write('userid,num_posts,botornot,self_declared_bot,news_bot,bridging_bot,amplifier_bot,cyborg,content_generation_bot,announcer_bot,repeater_bot\n')
        
        out_bias_filename = os.path.join(folder_to_run, file + '_botbias.json')

        users = {}

        with open(in_filename, 'r', encoding='utf-8') as f:
            for line in f:
                line_json = json.loads(line)
                userid = line_json['user']['id']
                if userid not in users:
                    users[userid] = []
                users[userid].append(line_json)

        for userid, user_tweets in users.items():
            try:
                check_type_of_bot(user_tweets, 'twitter_v1', userid)
            except:
                pass

        check_type_of_bias(users, 'twitter_v1')

        out_fh.close()

    return 1

def run_botsorter_twitter_v2(folder_to_run):
    global out_fh, out_bias_filename

    files_to_run = utils_model_helper.get_files_torun(folder_to_run)
    filtered_files = [file for file in files_to_run if '_bots.json' not in file]
    filtered_files = [file for file in filtered_files if '.tsv' not in file]

    for file in filtered_files:
        in_filename = os.path.join(folder_to_run, file)
        print(in_filename)

        out_filename = os.path.join(folder_to_run, file + '_botssorter.json')
        out_fh =  open(out_filename, 'w', encoding='utf-8')
        out_fh.write('userid,num_posts,botornot,self_declared_bot,news_bot,bridging_bot,amplifier_bot,cyborg,content_generation_bot,announcer_bot,repeater_bot\n')

        out_bias_filename = os.path.join(folder_to_run, file + '_botbias.json')

        users = {}

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

                if userid not in users:
                    users[userid] = []

                tweet['user'] = user_obj
                users[userid].append(tweet)                    

        for userid, user_tweets in users.items():
            try:
                check_type_of_bot(user_tweets, 'twitter_v2', userid)
            except:
                pass

        check_type_of_bias(users, 'twitter_v2')

        out_fh.close()

    return 1

def run_botsorter_reddit(folder_to_run):
    global out_fh, out_bias_filename

    files_to_run = utils_model_helper.get_files_torun(folder_to_run)
    filtered_files = [file for file in files_to_run if '_bots.json' not in file]
    filtered_files = [file for file in filtered_files if '.tsv' not in file]

    for file in filtered_files:
        in_filename = os.path.join(folder_to_run, file)
        print(in_filename)

        out_filename = os.path.join(folder_to_run, file + '_botssorter.json')
        out_fh =  open(out_filename, 'w', encoding='utf-8')
        out_fh.write('userid,num_posts,botornot,self_declared_bot,news_bot,bridging_bot,amplifier_bot,cyborg,content_generation_bot,announcer_bot,repeater_bot\n')

        out_bias_filename = os.path.join(folder_to_run, file + '_botbias.json')

        users = {}
        with open(in_filename, 'r', encoding='utf-8') as f:
            for line in f:
                line_json = json.loads(line)

                userid = line_json['id']
                if userid not in users:
                    users[userid] = []
                users[userid].append(line_json)

        for userid, user_tweets in users.items():
            try:
                check_type_of_bot(user_tweets, 'reddit', userid)
            except:
                pass

        check_type_of_bias(users, 'reddit')

        out_fh.close()

    return 1

def run_botsorter_instagram(folder_to_run):
    global out_fh, out_bias_filename
    
    files_to_run = utils_model_helper.get_files_torun(folder_to_run)
    filtered_files = [file for file in files_to_run if '_bots.json' not in file]
    filtered_files = [file for file in filtered_files if '.tsv' not in file]

    for file in filtered_files:
        in_filename = os.path.join(folder_to_run, file)
        print(in_filename)

        out_filename = os.path.join(folder_to_run, file + '_botssorter.json')
        out_fh =  open(out_filename, 'w', encoding='utf-8')
        out_fh.write('userid,num_posts,botornot,self_declared_bot,news_bot,bridging_bot,amplifier_bot,cyborg,content_generation_bot,announcer_bot,repeater_bot\n')

        out_bias_filename = os.path.join(folder_to_run, file + '_botbias.json')

        users = {}

        with open(in_filename, 'r', encoding='utf-8') as f:
            for line in f:
                line_json = json.loads(line)
                userid = line_json['user_id']

                if userid not in users:
                    users[userid] = []

                users[userid].append(line_json)

        for userid, user_tweets in users.items():
            try:
                check_type_of_bot(user_tweets, 'instagram', userid)
            except:
                pass

        #check_type_of_bias(users, 'instagram')

        out_fh.close()

    return 1

def run_botsorter_telegram(folder_to_run):
    global out_fh, out_bias_filename

    files_to_run = utils_model_helper.get_files_torun(folder_to_run)
    filtered_files = [file for file in files_to_run if '_bots.json' not in file]
    filtered_files = [file for file in filtered_files if '.tsv' not in file]

    for file in filtered_files:
        in_filename = os.path.join(folder_to_run, file)
        print(in_filename)

        out_filename = os.path.join(folder_to_run, file + '_botssorter.json')
        out_fh =  open(out_filename, 'w', encoding='utf-8')
        out_fh.write('userid,num_posts,botornot,self_declared_bot,news_bot,bridging_bot,amplifier_bot,cyborg,content_generation_bot,announcer_bot,repeater_bot\n')

        out_bias_filename = os.path.join(folder_to_run, file + '_botbias.json')
        
        users = {}

        with open(in_filename, 'r', encoding='utf-8') as f:
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
                    
                    userid = user_data['id']
                    if userid not in users:
                        users[userid] = []
                    users[userid].append(message)

        for userid, user_tweets in users.items():
            try:
                check_type_of_bot(user_tweets, 'telegram', userid)
            except:
                pass

        check_type_of_bias(users, 'telegram')

        out_fh.close()
    
    return 1


import pandas as pd
import collections
import itertools
from sentence_transformers import util
import numpy as np

import utils_model_helper

def get_usernames(first_item, platform):
    if platform == 'twitter_v1':
        username = first_item['user']['name']
        screenname = first_item['user']['screen_name']
        description = first_item['user']['description']
    elif platform == 'twitter_v2':
        username = first_item['user']['username']
        screenname = first_item['user']['name']
        description = first_item['user']['description']
    elif platform == 'instagram':
        username = first_item['username']
        screenname = first_item['fullname']
        description = None
    elif platform == 'reddit':
        username = first_item['author_fullname']
        screenname = first_item['author']
        description = None
    elif platform == 'telegram':
        username = first_item['user']['username']
        screenname = first_item['user']['first_name'] + first_item['user']['last_name']
        description = None

    return username, screenname, description

def check_if_self_declared_bot(data, platform):
    first_item = data[0]
    username, screenname, description = get_usernames(first_item, platform)

    if screenname is not None:
        screenname = screenname.lower()
        if 'bot' in screenname:
            return True
    elif username is not None:
        username = username.lower()
        if 'bot' in username:
            return True
    elif description is not None:
        description = description.lower()
        if 'bot' in description:
            return True
    return False

def get_text_field(first_item, platform):
    if platform == 'twitter_v1':
        if 'full_text' in first_item:
            text_field = 'full_text'
        else:
            text_field = 'text'
    elif platform == 'twitter_v2':
        text_field = 'text'
    elif platform == 'instagram':
        text_field = None
    elif platform == 'reddit':
        text_field = 'selftext'
    elif platform == 'telegram':
        text_field = 'message'

    return text_field

def check_if_amplifier_bot(data, platform):
    first_item = data[0]
    text_field = get_text_field(first_item, platform)

    amplifier_ref_mentions = 0
    amplifier_ref_retweet = 0

    for post in data:
        text = post[text_field]

        if text == '' or text == None:
            return False 
        
        if text.startswith('RT'):
            amplifier_ref_retweet += 1

        sentence_split = text.split(' ')
        for w in sentence_split:
            if w.startswith('@'):
                amplifier_ref_mentions += 1
                break

    perc_threshold = (len(data) * 0.80)

    if amplifier_ref_retweet >= perc_threshold:
        is_amplifier_bot = True
    elif amplifier_ref_mentions >= perc_threshold:
        is_amplifier_bot = True
    elif (amplifier_ref_mentions + amplifier_ref_retweet) >= perc_threshold:
        is_amplifier_bot = True
    else:
        is_amplifier_bot = False
                
    return is_amplifier_bot

def predict_tweet_or_news(text, news_model):
    preproc_text = utils_model_helper.preprocess_text(text)
    text_arr = [preproc_text]
    df_test = pd.DataFrame(text_arr, columns=['text'])
    pred = news_model.predict(df_test)
    return pred[0]

def check_if_news_bot(data, platform, news_model):
    first_item = data[0]
    username, screenname, description = get_usernames(first_item, platform)

    if screenname is not None:
        screenname = screenname.lower()
        if 'news' in screenname:
            return True
    if username is not None:
        username = username.lower()
        if 'news' in username:
            return True
    if description is not None:
        description = description.lower()
        if 'news' in description:
            return True
    
    # for each tweet, check if it is news
    news_or_not_arr = []
    first_item = data[0]
    text_field = get_text_field(first_item, platform)
    
    for post in data: 
        text = post[text_field]

        if text == '' or text == None:
            news_or_not = 'not'
        else:
            processed_text = utils_model_helper.preprocess_text(text)
            if processed_text == '' or processed_text == None:
                news_or_not = 'not'
            else:
                news_or_not = predict_tweet_or_news(processed_text, news_model)

        news_or_not_arr.append(news_or_not)

    arr_counter = collections.Counter(news_or_not_arr)
    if (arr_counter['news'] / len(news_or_not_arr)) >= 0.80:
        is_news_bot = True
    else:
        is_news_bot = False

    return is_news_bot

def check_if_bridging_bot(data, platform):
    first_item = data[0]
    text_field = get_text_field(first_item, platform)

    num_more_than_2 = 0

    for post in data:
        text = post[text_field]

        if text == '' or text == None:
            return False
        
        sentence_split = text.split(' ')
        num_mentions = 0
        for w in sentence_split:
            if w.startswith('@'):
                num_mentions += 1

        if num_mentions >= 2:
            num_more_than_2 += 1

        num_tweets = len(data)
        if num_more_than_2 >= (num_tweets * 0.80):
            return True
        else:
            return False

    return False 

def check_if_content_generation_bot(data, platform):
    is_original = 0
    first_item = data[0]
    text_field = get_text_field(first_item, platform)

    for post in data:
        text = post[text_field]

        if text == '' or text == None:
            continue
        else:
            if not text.startswith('RT'):
                is_original += 1

    if is_original >= (0.80 * len(data)):
        return True
    else:
        return False

def get_sim_arr(text_list, sentence_model):
    sim_arr = []

    for pair in itertools.combinations(text_list, 2):
        embedding_1 = sentence_model.encode(pair[0], convert_to_tensor=True)
        embedding_2 = sentence_model.encode(pair[1], convert_to_tensor=True)

        similarity = util.pytorch_cos_sim(embedding_1, embedding_2)
        sim_arr.append(similarity[0][0].item())

    return sim_arr

def check_if_repeater_bot(data, platform, sentence_model):
    first_item = data[0]
    text_field = get_text_field(first_item, platform)

    text_list = []

    for post in data:
        text = post[text_field]
        
        if text == '' or text == None:
            continue
        else:
            preprocessed_text = utils_model_helper.preprocess_text(text)
            if preprocessed_text != '':
                text_list.append(preprocessed_text)

    sim_arr = get_sim_arr(text_list, sentence_model)
    
    try:
        if len(sim_arr) == 0:
            return False

        if np.array(sim_arr).mean() >= 0.50:
            return True
        else:
            return False
    except:
        return False

def get_date_field(platform):
    if platform == 'twitter_v1' or platform == 'twitter_v2':
        date_field = 'created_at'
    elif platform == 'instagram':
        date_field = None
    elif platform == 'reddit':
        date_field = 'created_utc'
    elif platform == 'telegram':
        date_field = 'date'

    return date_field

def get_periodicity(signal):    
    if len(signal) <= 10:
        return False, None
        
    try:
        df_signal = signal
        
        diff_between_peaks = [x - df_signal[i - 1] for i, x in enumerate(df_signal)][1:]
        
        if len(diff_between_peaks) == 1:
            return True, diff_between_peaks[0]

        b = collections.Counter(diff_between_peaks)
        most_common_val = b.most_common()[0][1]
        
        if most_common_val >= (0.5 * len(diff_between_peaks)):
            return True, most_common_val
        else:
            return False, None
    except:
        return False, None

def check_if_announcer_bot(data, platform):
    date_field = get_date_field(platform)
    if date_field == None:
        return False

    df_post_dict = pd.DataFrame.from_dict(data)
    df_post_dict[date_field] = pd.to_datetime(df_post_dict[date_field])
    df_time = df_post_dict[date_field].dt.floor('H').value_counts().rename_axis('date').reset_index(name='count')
    
    df_time_arr = df_time['count'].tolist()
    
    periodicity, most_common_val = get_periodicity(df_time_arr)
    
    if periodicity == False:
        return False
    else:
        return True   

def get_posts_prob(text, posts_model):
    #text_cleaned = preprocess_text(text)
    #text_dict = [{'text_cleaned': text_cleaned}]
    text_dict = [{'text_cleaned': text}]
    df = pd.DataFrame(text_dict)
    
    post_text_prob = posts_model.predict_proba(df)
    bot_prob = post_text_prob[0][0]
    #human_prob = post_text_prob[0][1]
        
    return bot_prob

def check_if_cyborg(data, platform, post_model):
    if len(data) <= 3:
        return False
    
    initial_bot = None
    initial_botscore = None
    
    num_flip = 0
    change_in_score = 0.0
    count = 0

    first_item = data[0]
    text_field = get_text_field(first_item, platform)

    for post in data:
        text = post[text_field]

        if text != '' and text is not None:                
            botscore = get_posts_prob(text, post_model)
            if botscore >= 0.5:
                bot_or_not = True
            else:
                bot_or_not = False

            if initial_bot == None:
                initial_bot = bot_or_not
                initial_botscore = botscore
            else:
                if bot_or_not != initial_bot:
                    num_flip += 1

                    initial_bot = bot_or_not

                botscore_change = abs(initial_botscore - botscore)
                change_in_score += botscore_change

            count += 1

    if num_flip >= 3 or change_in_score >= 0.02:
        return True
    else:
        return False
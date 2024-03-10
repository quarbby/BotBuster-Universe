import itertools
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from sentence_transformers import util
from collections import Counter

import botsorter_algo

analyzer = SentimentIntensityAnalyzer()

def get_retweet_quote_reply_fields(platform):
    if platform == 'twitter_v1':
        retweet = 'retweeted_status'
        quote = 'is_quote_status'   # boolean
        reply = 'in_reply_to_user_id'
    elif platform == 'twitter_v2':
        retweet = 'referenced_tweets'
        quote = 'referenced_tweets'
        reply = 'referenced_tweets'
    elif platform == 'instagram':
        retweet = None
        quote = None 
        reply = None 
    elif platform == 'reddit':
        retweet = None
        quote = None 
        reply = None 
    elif platform == 'telegram':
        retweet = 'fwd_from'
        quote = None
        reply = 'reply_to'

    return retweet, quote, reply

def get_username(post, platform):
    if platform == 'twitter_v1' or platform == 'twitter_v2':
        username = post['user']['screen_name']
    elif platform == 'instagram':
        username = None
    elif platform == 'reddit':
        username = post['author']
    elif platform == 'telegram':
        username = post['user']['first_name'] + post['user']['last_name']

    return username

def check_homophily(post, platform, identities_terms):
    try:
        retweet_field, quote_field, reply_field = get_retweet_quote_reply_fields(platform)

        username = get_username(post, platform)

        is_retweet = post[retweet_field]
        is_quote = post[quote_field]
        is_reply = post[reply_field]

        message_field = botsorter_algo.get_text_field(post, platform)
        message = post[message_field]

        if is_retweet or is_quote or is_reply:
            source_label = username
            source_identities = [term for term in identities_terms if term in source_label]
            message_split = message.split(' ')

            for w in message_split:
                if w.startswith('@'):
                    w = w.lower()
                    target_identities = [term for term in identities_terms if term in w]
                    
                    common_identities = set(source_identities) & set(target_identities)
                    if common_identities:
                        return True
                    
        return False
    except:
        return False

def check_authority(post, platform, authority_terms):
    message_field = botsorter_algo.get_text_field(post, platform)
    message = post[message_field]
    message_split = message.split(' ')

    authority_list = []
    for w in message_split:
        authority_presence = [term for term in authority_terms if term in w]
        authority_list += authority_presence

    if len(authority_list) >= 1:
        return True
    else:
        return False

def get_sentiment_type(compoundsentiment):
    if compoundsentiment >= 0.05:
        return 'positive'
    elif compoundsentiment <= -0.05:
        return 'negative'
    elif (compoundsentiment > -0.05) and (compoundsentiment < 0.05):
        return 'neutral'
    
    return 'neutral'

def check_affect(post, platform):
    global SentimentIntensityAnalyzer
    positive = False
    negative = False 

    message_field = botsorter_algo.get_text_field(post, platform)
    message = post[message_field]

    vs = analyzer.polarity_scores(message)
    compound_score = vs['compound']
    sentiment_type = get_sentiment_type(compound_score)

    if sentiment_type == 'positive':
        positive = True
        negative = False 
    elif sentiment_type == 'negative':
        positive = False
        negative = True 
    elif sentiment_type == 'neutral':
        positive = False
        negative = False

    return positive, negative, compound_score

def check_illusory_truth(data, platform, sentence_model):
    if len(data) < 2:
        return None 

    first_item = data[0]
    message_field = botsorter_algo.get_text_field(first_item, platform)

    postlist = []
    sim_arr = []

    for post in data:
        postlist.append({'message': post[message_field], 'postid': post['id']})

    for pair in itertools.combinations(postlist, 2):
        embedding_1 = sentence_model.encode(pair[0]['message'], convert_to_tensor=True)
        embedding_2 = sentence_model.encode(pair[1]['message'], convert_to_tensor=True)

        similarity_obj = util.pytorch_cos_sim(embedding_1, embedding_2)
        similarity = similarity_obj[0][0].item()
        if similarity >= 0.6:
            sim_arr.append((pair[0]['postid'], pair[1]['postid'], similarity))

    similar_post_indices = []
    for similar_posts in sim_arr:
        postid1 = similar_posts[0]
        postid2 = similar_posts[1]
        if postid1 not in similar_post_indices:
            similar_post_indices.append(postid1)
        if postid2 not in similar_post_indices:
            similar_post_indices.append(postid2)

    return similar_post_indices

def check_availability(data, platform):
    if len(data) < 2:
        return None 

    retweet_field, quote_field, reply_field = get_retweet_quote_reply_fields(platform)

    count = 0

    avail_posts = []

    for post in data:
        postid = post['id']
        
        if retweet_field in post:
            if post[retweet_field]:
                count += 1
        if quote_field in post:
            if post[quote_field]:
                count += 1
        if reply_field in post:
            if post[reply_field]:
                count += 1

        avail_posts.append(postid)

    if len(avail_posts) >= 3:
        return avail_posts
    else:
        return None 


def check_confirmation(sentiment_list):
    if len(sentiment_list) < 2:
        return None 

    sentiment_filtered = []
    postid_filtered = []

    for postid, compoundsentiment in sentiment_list:
        sentiment_type = get_sentiment_type(compoundsentiment)
        if sentiment_type != 'neutral':
            sentiment_filtered.append(sentiment_type)
            postid_filtered.append(postid)

    counts = Counter(sentiment_filtered)
    num_positives = counts.get('positive', 0)
    num_negatives = counts.get('negative', 0)

    postid_final = []

    if num_positives > 3:
        positive_indices = [i for i, item in enumerate(sentiment_filtered) if item == 'positive']

        for idx in positive_indices:
            postid_final.append(postid_filtered[idx])

    if num_negatives > 3:
        negative_indices = [i for i, item in enumerate(sentiment_filtered) if item == 'negative']

        for idx in negative_indices:
            postid_final.append(postid_filtered[idx])

    if len(postid_final) > 0:
        return postid_final
    else:
        return None
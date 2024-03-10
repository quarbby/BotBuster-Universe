import re, os
import pandas as pd
from math import log
import string
import emoji

username_cols = ['entropy', 'num_uppercase', 'num_lowercase', 'num_digits', 'num_punctuations', 'num_emojis', 'num_hashtags']
screenname_cols = ['entropy', 'num_uppercase', 'num_lowercase', 'num_digits', 'num_punctuations', 'num_emojis', 'num_hashtags', 'num_words']
usermetadata_cols = ['followers_count', 'following_count', 'listed_count', 'protected', 'verified', 'tweet_count', 'like_count']
posts_data_cols = ['post_like_count', 'post_retweet_count', 'post_reply_count', 'post_quote_count']

reaction_dict = {'👍': 'up', '❤': 'up', '👏': 'up', '🔥': 'up', '👎': 'down', '🤯': 'up', '😁': 'up', '💯': 'up',
                '😱': 'down', '🤔': 'unknown', '🥰': 'up', '😢': 'down', '🤣': 'up', '❤\u200d🔥': 'up', '🙏': 'up',
                '🎉': 'up', '👌': 'up', '🤩': 'up', '🤡': 'down', '🤮': 'down', '😈': 'unknown', '😭': 'down', '🤬': 'down', 
                '\U0001fae1': 'up', '💩': 'down', '🏆': 'up', '🍾': 'up', '⚡': 'up', '🕊': 'up', '😴': 'down', '🌭': 'unknown',
                '😇': 'up', '🥴': 'unknown', '🤓': 'unknown', '😍': 'up', '💔': 'down', '👀': 'unknown', '😨': 'down', '🤨': 'down',
                '🖕': 'down', '🥱': 'down', '🤪': 'up', '🌚': 'unknown', '😐': 'unknown', '🙈': 'unknown', '🆒': 'up',
                '👾': 'unknown', '👻': 'unknown', '🐳': 'unknown', '✍': 'unknown', '💘': 'up', '🙊': 'unknown', '💊': 'unknown',
                '🤝': 'up', '🤗': 'up', '🙉': 'unknown', '😡': 'down', '🦄': 'up', '👨\u200d💻': 'up', '🗿': 'unknown',
                '🍌': 'unknown', '🎃': 'unknown', '☃': 'unknown', '😎': 'up', '🤷\u200d♀': 'unknown', '💋': 'up', '💅': 'unknown',
                '🍓': 'unknown', '😘': 'up', '🤷\u200d♂': 'unknown', '🤷': 'unknown', '🎅': 'unknown', '🎄': 'unknown'
                }

def get_files_torun(folder_to_run):
    files_to_run = os.listdir(folder_to_run)

    return files_to_run

def user_json_to_dict(user_json_arr):
    user_dict = {}
    for u in user_json_arr:
        userid = u['id']
        user_dict[userid] = u
    
    return user_dict

# Functions for username and screenname

def log2(number): 
    return log(number)/log(2)

df_entropy = pd.read_csv('./models/names_dict.csv')
df_entropy['log2'] = df_entropy['probability'].apply(log2)
df_entropy_dict = df_entropy.set_index('character').to_dict()

def get_entropy_of_text(text):
    text = text.lower()
    entropy = 0.0
    if not text:
        return -1

    #text = remove_punctuations(text)
    for char in text:
        if char in df_entropy_dict['log2']:
            entropy += df_entropy_dict['log2'][char]

    return -entropy


def get_num_uppercase_letters(text):
    return sum(1 for c in text if c.isupper())

def get_num_lowercase_letters(text):
    return sum(1 for c in text if c.islower())

def get_num_digits(text):
    return sum(1 for c in text if c.isdigit())

def get_num_punctuations(text):
    count = lambda l1,l2: sum([1 for x in l1 if x in l2])
    return count(text, set(string.punctuation))

def get_num_hashtags(text):
    return sum(1 for c in text if c=='#')

def get_num_emojis(text):
    return len(''.join(c for c in text if c in emoji.UNICODE_EMOJI['en']))

def get_num_spaced_words(text):
    return len(text.split(' '))

def get_num_words(text):
    return len(re.findall(r'\w+', text))

# col_name is user_name or screen_name
def transform_df(df, col_name):
    df['entropy'] = df[col_name].apply(get_entropy_of_text)
    df['num_uppercase'] = df[col_name].apply(get_num_uppercase_letters)
    df['num_lowercase'] = df[col_name].apply(get_num_lowercase_letters)
    df['num_digits'] = df[col_name].apply(get_num_digits)
    df['num_punctuations'] = df[col_name].apply(get_num_punctuations)
    df['num_emojis'] = df[col_name].apply(get_num_emojis)
    df['num_hashtags'] = df[col_name].apply(get_num_hashtags)
    df['num_words'] = df[col_name].apply(get_num_spaced_words)
    
    return df

# Functions for description and posts 
def preprocess_text(text):
    text = text.lower()
    text_cleaned = ' '.join(re.sub("(@[A-Za-z0-9]+)|([^0-9A-Za-z \t])|(\w+:\/\/\S+)"," ", text).split())
    text_cleaned = re.sub(r'^https?:\/\/.*[\r\n]*', '', text_cleaned)
    return text_cleaned

# Data reading processing functions
def convert_true_false_to_binary(val):
    if val == True:
        return 1
    elif val == False:
        return 0
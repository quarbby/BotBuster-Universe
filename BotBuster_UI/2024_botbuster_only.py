import botbuster
import utils_model_helper
import os, json
import pandas as pd

folder_to_run = r'C:\Users\lynne\Documents\2024_cysoc_sam\test'
file_to_analyze = r'C:\Users\lynne\Documents\2024_cysoc_sam\test\test.json'

out_fh = None

def form_usermetadata_twitter_v1(line_json):
    user_metadata_arr = [{'userid': line_json['uid'],
                          'followers_count': line_json['followers_count'],
                          'following_count': line_json['friends_count'],
                          'listed_count': -1,
                          'protected': utils_model_helper.convert_true_false_to_binary(line_json['protected']),
                          'verified': utils_model_helper.convert_true_false_to_binary(line_json['verified']),
                          'like_count': -1,
                          'tweet_count': line_json['statuses_count']
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
                    userid = line_json['uid']
                    username = line_json['name']
                    screenname = line_json['screen_name']
                    description = line_json['description']
                    is_verified = line_json['verified']
                    
                    df_posts = None
                    df_usermetadata = form_usermetadata_twitter_v1(line_json)
                    
                    botbuster.compute_botbuster_prob(out_fh, userid, username, screenname, description, is_verified, df_posts, df_usermetadata)
                except Exception as e:
                    print(e)
                    pass

        out_fh.close()

        return 1

model_reading = botbuster.read_models()

botbuster_run = run_botbuster_twitter_v1(folder_to_run)


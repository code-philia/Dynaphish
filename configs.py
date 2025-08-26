import os

repo_dir = os.path.dirname(os.path.abspath(__file__))
repo_dir_parent = os.path.dirname(repo_dir)

google_cloud_json_credentials = repo_dir + "/knowledge_expansion/discoverylabel.json"
google_search_credentials     = repo_dir + '/knowledge_expansion/api_key.txt'
assert os.path.exists(google_cloud_json_credentials)
assert os.path.exists(google_search_credentials)


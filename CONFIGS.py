import os

repo_dir = os.path.dirname(os.path.abspath(__file__))
repo_dir_parent = os.path.dirname(repo_dir)

mmocr_config_path = repo_dir_parent + "/MyXdriver_pub/configs/"
button_locator_config = repo_dir_parent + "/MyXdriver_pub/xutils/forms/button_locator_models/config.yaml"
button_locator_weights_path = repo_dir_parent + "/MyXdriver_pub/xutils/forms/button_locator_models/model_final.pth"
assert os.path.exists(mmocr_config_path)
assert os.path.exists(button_locator_config)
assert os.path.exists(button_locator_weights_path)

google_cloud_json_credentials = repo_dir + "/knowledge_expansion/discoverylabel.json"
google_search_credentials = repo_dir + '/knowledge_expansion/api_key.txt'
assert os.path.exists(google_cloud_json_credentials)
assert os.path.exists(google_search_credentials)

user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"

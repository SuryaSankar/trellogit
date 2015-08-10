import requests
import os
from flask.config import Config

config = Config(os.getcwd())
config.from_pyfile("app.cfg.py")


# ######## Sample cfg file ##################################
# GITHUB_TOKEN = "ewrwtweatweatwetewtewd8"                  #

# TRELLO_KEY = "afbakseaweweoiaewoit"                       #

# TRELLO_SECRET = "sdgjoasidguadsoigu"                      #

# TRELLO_TOKEN = "askshgkasdjghalskdghjasdlkj"              #

# MILESTONES_BOARD_ID = "dsgkasdhgaksdjghasdlkghj"          #

# TASKS_BOARD_ID = "jalksfjasldkgdshakg"                    #

# TASKS_BOARD_DEV_LABEL_ID = "lkjlpjlkjlpjlkjlpjlkj"        #

# MILESTONES_TODO_LIST_ID = 'ljlkhlkhlkhlkkkhlkhlkhlkh'     #

# TASKS_BOARD_LISTS = {                                     #
#     'To Do': "ljlkhlkhlkhlkhlkhlk"                        #
# }

# REPO_OWNER = "inkmonk"                                    #

# REPO_NAME = "trellogit"                                   #


# GIT_TO_TRELLO = {                                         #
#     'SuryaSankar': 'oiu9809uuoi',                         #
#     'seekshiva': '30985q098f9fsudifueosi',                #
#     'isaacjohnwesley': '0938qasfiaeoiru',                 #
#     'psibi': '0q938alskfarlkjlkjlk'                       #
# }                                                         #
##############################################################


trello_api = "https://api.trello.com/1"
github_api = "https://api.github.com"

trello = requests.Session()
github = requests.Session()

trello.params.update({
    'key': config['TRELLO_KEY'],
    "token": config['TRELLO_TOKEN']
})

github.headers.update({'Authorization': 'token %s' % config['GITHUB_TOKEN']})


def github_to_trello_sync():
    trello_milestones = []

    milestones = github.get("%s/repos/%s/%s/milestones" % (
        github_api, config['REPO_OWNER'], config['REPO_NAME'])).json()

    for m in milestones:
        if m['state'] == 'open':
            gh_issues = github.get(
                "%s/repos/%s/%s/issues" % (github_api, config['REPO_OWNER'], config['REPO_NAME']),
                params={"milestone": int(m['number'])}).json()
            issues = []
            for i in gh_issues:
                issues.append({
                    'assignee': i['assignee']['login'],
                    'html_url': i['html_url'],
                    'title': i['title'],
                    'id': i['url'].rpartition('/')[-1]
                })
            card = {
                "name": m['title'] + "#%s" % m['number'],
                "idList": config['MILESTONES_TODO_LIST_ID'],
                "due": m['due_on'],
                "desc": m['description'][:16383],
                "idMembers": ",".join(
                    list(set(config['GIT_TO_TRELLO'][i['assignee']] for i in issues)))
            }
            trello_milestones.append({
                'card': card,
                'issues': issues
            })

    for m in trello_milestones:
        r = trello.post("https://api.trello.com/1/cards", data=m['card'])
        r = trello.post("https://api.trello.com/1/labels", data={
            'name': m['card']['name'],
            'color': None,
            'idBoard': config['TASKS_BOARD_ID']
        })
        milestone_label_id = r.json()['id']

        for issue in m['issues']:
            issue_card = {
                "name": issue['title'] + "#%s" % issue['id'],
                "idList": config['TASKS_BOARD_LISTS']['To Do'],
                "due": m['card']['due'],
                "desc": issue['html_url'],
                "idMembers": config['GIT_TO_TRELLO'][issue['assignee']],
                "idLabels": ",".join([milestone_label_id, config['TASKS_BOARD_DEV_LABEL_ID']])
            }
            trello.post("https://api.trello.com/1/cards", data=issue_card)


def trello_tasks_to_milestone_checklists_sync():
    pass

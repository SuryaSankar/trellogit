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


existing_gh_milestones = github.get("%s/repos/%s/%s/milestones" % (
    github_api, config['REPO_OWNER'], config['REPO_NAME'])).json()

existing_milestone_labels = trello.get("%s/boards/%s/labels" % (
    trello_api, config['TASKS_BOARD_ID'])).json()
print existing_milestone_labels

existing_milestone_cards = trello.get(
    "%s/boards/%s/cards" % (trello_api, config['MILESTONES_BOARD_ID'])).json()

existing_issue_cards = trello.get(
    "%s/boards/%s/cards" % (trello_api, config['TASKS_BOARD_ID'])).json()


def github_to_trello_sync():

    for m in existing_gh_milestones:
        gh_issues = github.get(
            "%s/repos/%s/%s/issues" % (github_api, config['REPO_OWNER'], config['REPO_NAME']),
            params={"milestone": int(m['number'])}).json()

        try:
            milestone_label = next(
                label for label in existing_milestone_labels
                if label['name'].endswith('#%s' % m['number']))
        except StopIteration:
            milestone_label = trello.post("https://api.trello.com/1/labels", data={
                'name': "%s#%s" % (m['title'], m['number']),
                'color': 'green',
                'idBoard': config['TASKS_BOARD_ID']
            }).json()

        issue_cards = []
        for issue in gh_issues:
            if issue['state'] == 'closed':
                list_to_be_added_to = config['TASKS_BOARD_LISTS']['Done']
            else:
                list_to_be_added_to = config['TASKS_BOARD_LISTS']['To Do']
                if issue['comments'] == 0:
                    issue_events = github.get(issue['events_url']).json()
                    if any(event['commit_id'] is not None for event in issue_events):
                        list_to_be_added_to = config['TASKS_BOARD_LISTS']['Doing']

            try:
                issue_card = next(
                    card for card in existing_issue_cards
                    if card['name'].endswith("#%s" % issue['number']))
                data_to_update = {}
                if issue_card['due'] != m['due_on']:
                    data_to_update['due'] = m['due_on']
                if issue_card['name'].rpartition("#")[0] != issue['title']:
                    data_to_update['name'] = "%s#%s" % (issue['title'], issue['number'])
                if issue_card['idList'] != list_to_be_added_to:
                    data_to_update['idList'] = list_to_be_added_to
                if issue_card['idMembers'] != config['GIT_TO_TRELLO'][issue['assignee']['login']]:
                    data_to_update['idMembers'] = config[
                        'GIT_TO_TRELLO'][issue['assignee']['login']]
                if len(data_to_update.keys()) > 0:
                    issue_card = trello.put("%s/cards/%s" % (
                        trello_api, issue_card['id']), data=data_to_update).json()
            except StopIteration:
                issue_card = {
                    "name": issue['title'] + "#%s" % issue['number'],
                    "idList": list_to_be_added_to,
                    "due": m['due_on'],
                    "desc": issue['html_url'],
                    "idMembers": config['GIT_TO_TRELLO'][issue['assignee']['login']],
                    "idLabels": ",".join(
                        [milestone_label['id'], config['TASKS_BOARD_DEV_LABEL_ID']])
                }
                issue_card = trello.post("https://api.trello.com/1/cards", data=issue_card).json()
            issue_cards.append(issue_card)

        if all(card['idList'] == config['TASKS_BOARD_LISTS']['Done'] for card in issue_cards):
            milestone_list_to_use = config['MILESTONES_BOARD_LISTS']['Done']
        elif any(card['idList'] in (
                config['TASKS_BOARD_LISTS']['Doing'],
                config['TASKS_BOARD_LISTS']['Done']) for card in issue_cards):
            milestone_list_to_use = config['MILESTONES_BOARD_LISTS']['Doing']
        else:
            milestone_list_to_use = config['MILESTONES_BOARD_LISTS']['To Do']

        members_to_assign = ",".join(
            list(set(config['GIT_TO_TRELLO'][i['assignee']['login']] for i in gh_issues)))

        try:
            card = next(card for card in existing_milestone_cards
                        if card['name'].endswith('#%s' % m['number']))
            card_data_to_update = {}
            if card['due'] != m['due_on']:
                card_data_to_update['due'] = m['due_on']
            if card['name'].rpartition("#")[0] != m['title']:
                card_data_to_update['name'] = "%s#%s" % (m['title'], m['number'])
            if card['idList'] != milestone_list_to_use:
                card_data_to_update['idList'] = milestone_list_to_use
            if card['idMembers'] != members_to_assign:
                card_data_to_update['idMembers'] = members_to_assign
            if len(card_data_to_update.keys()) > 0:
                trello.put("%s/cards/%s" % (
                    trello_api, card['id']), data=card_data_to_update)

        except StopIteration:
            card = {
                "name": "%s#%s" % (m['title'], m['number']),
                "idList": milestone_list_to_use,
                "due": m['due_on'],
                "desc": m['description'][:16383],
                "idMembers": members_to_assign
            }
            trello.post("https://api.trello.com/1/cards", data=card)


def trello_tasks_to_milestone_checklists_sync():
    pass

if __name__ == '__main__':
    github_to_trello_sync()

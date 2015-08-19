import requests
import os
# from flask.config import Config
from itertools import groupby
from toolspy import keygetter
from flask import Flask, render_template, request, Response
import json
from flask_sqlalchemy_booster.responses import jsoned

# config = Config(os.getcwd())
# config.from_pyfile("app.cfg.py")


# ######## Sample cfg file ##################################
# GITHUB_TOKEN = "ewrwtweatweatwetewtewd8"                  #

# TRELLO_KEY = "afbakseaweweoiaewoit"                       #

# TRELLO_SECRET = "sdgjoasidguadsoigu"                      #

# TRELLO_TOKEN = "askshgkasdjghalskdghjasdlkj"              #

# MILESTONES_BOARD_ID = "dsgkasdhgaksdjghasdlkghj"          #

# TASKS_BOARD_ID = "jalksfjasldkgdshakg"                    #

# TASKS_BOARD_DEV_LABEL_ID = "lkjlpjlkjlpjlkjlpjlkj"        #

# REPO_OWNER = "inkmonk"                                    #

# REPO_NAME = "trellogit"                                   #


# GIT_TO_TRELLO = {                                         #
#     'SuryaSankar': 'oiu9809uuoi',                         #
#     'seekshiva': '30985q098f9fsudifueosi',                #
#     'isaacjohnwesley': '0938qasfiaeoiru',                 #
#     'psibi': '0q938alskfarlkjlkjlk'                       #
# }                                                         #
##############################################################

app = Flask(__name__)

trello_api = "https://api.trello.com/1"
github_api = "https://api.github.com"

trello = requests.Session()
github = requests.Session()

trello.params.update({
    'key': os.environ['TRELLO_KEY'],
    "token": os.environ['TRELLO_TOKEN']
})

github.headers.update({'Authorization': 'token %s' % os.environ['GITHUB_TOKEN']})


# existing_gh_milestones = github.get("%s/repos/%s/%s/milestones" % (
#     github_api, os.environ['REPO_OWNER'], os.environ['REPO_NAME'])).json()

class OneTimeSyncer(object):

    def __init__(self):

        self.git_to_trello_assignee_map = json.loads(os.environ["GIT_TO_TRELLO"])

        # self.tasks_board_lists = config.get('TASKS_BOARD_LISTS', {})

        # if self.tasks_board_lists == {}:
        self.tasks_board_lists = {}
        lists = trello.get(
            "%s/boards/%s/lists" % (trello_api, os.environ['TASKS_BOARD_ID'])).json()
        for lst in lists:
            self.tasks_board_lists[lst['name']] = lst['id']

        # self.milestones_board_lists = config.get('MILESTONES_BOARD_LISTS', {})

        # if self.milestones_board_lists == {}:
        self.milestones_board_lists = {}
        lists = trello.get(
            "%s/boards/%s/lists" % (trello_api, os.environ['MILESTONES_BOARD_ID'])).json()
        for lst in lists:
            self.milestones_board_lists[lst['name']] = lst['id']

        self.milestones_board = trello.get(
            "%s/boards/%s" % (trello_api, os.environ['MILESTONES_BOARD_ID'])).json()
        os.environ['MILESTONES_BOARD_ID'] = self.milestones_board['id']

        self.tasks_board = trello.get(
            "%s/boards/%s" % (trello_api, os.environ['TASKS_BOARD_ID'])).json()
        os.environ['TASKS_BOARD_ID'] = self.tasks_board['id']

    def fetch_existing_github_state(self):
        self.existing_milestone_labels = trello.get("%s/boards/%s/labels" % (
            trello_api, os.environ['TASKS_BOARD_ID'])).json()

        self.existing_milestone_cards = trello.get(
            "%s/boards/%s/cards" % (trello_api, os.environ['MILESTONES_BOARD_ID'])).json()

        self.existing_issue_cards = trello.get(
            "%s/boards/%s/cards" % (trello_api, os.environ['TASKS_BOARD_ID'])).json()

        self.issues_response = github.get(
            "%s/repos/%s/%s/issues" % (github_api, os.environ['REPO_OWNER'], os.environ['REPO_NAME']),
            params={"state": "all", "per_page": 100})

        self.issues = []

        self.issues += self.issues_response.json()

        self.page_links_extracter = lambda response: dict(
            [list(reversed(map(lambda w: w.strip().strip("<").strip(">"), l.split(";"))))
             for l in response.headers['link'].split(",")])

        self.page_links_in_header = self.page_links_extracter(self.issues_response)

        while 'rel="next"' in self.page_links_in_header:
            self.issues_response = github.get(self.page_links_in_header['rel="next"'])
            self.issues += self.issues_response.json()
            self.page_links_in_header = self.page_links_extracter(self.issues_response)

        self.grouped_issues = list(
            (key, list(items)) for key, items in
            groupby(sorted(self.issues, key=keygetter('milestone')), key=keygetter('milestone')))

    def update_or_create_task_card(self, issue, milestone=None, milestone_label=None):
        if issue['state'] == 'closed':
            list_to_be_added_to = self.tasks_board_lists['Done']
        else:
            if milestone is None:
                list_to_be_added_to = self.tasks_board_lists['Backlog']
            else:
                list_to_be_added_to = self.tasks_board_lists['To Do']
            if issue['comments'] == 0:
                issue_events = github.get(issue['events_url']).json()
                if any(event['commit_id'] is not None for event in issue_events):
                    list_to_be_added_to = self.tasks_board_lists['Doing']

        try:
            issue_card = next(
                card for card in self.existing_issue_cards
                if card['name'].endswith("#%s" % issue['number']))
            data_to_update = {}
            if milestone is not None:
                if issue_card['due'] != milestone['due_on']:
                    data_to_update['due'] = milestone['due_on']
            if issue_card['name'].rpartition("#")[0] != issue['title']:
                data_to_update['name'] = "%s#%s" % (issue['title'], issue['number'])
            if issue_card['idList'] != list_to_be_added_to:
                data_to_update['idList'] = list_to_be_added_to
            if issue['assignee'] is not None:
                if issue_card['idMembers'] != self.git_to_trello_assignee_map[issue['assignee']['login']]:
                    data_to_update['idMembers'] = self.git_to_trello_assignee_map[issue['assignee']['login']]
            if len(data_to_update.keys()) > 0:
                issue_card = trello.put("%s/cards/%s" % (
                    trello_api, issue_card['id']), data=data_to_update).json()
        except StopIteration:
            issue_card = {
                "name": issue['title'] + "#%s" % issue['number'],
                "idList": list_to_be_added_to,
                "desc": issue['html_url']
            }
            if milestone is not None:
                issue_card["due"] = milestone['due_on']
            if milestone_label is not None:
                issue_card["idLabels"] = ",".join(
                    [milestone_label['id'], os.environ['TASKS_BOARD_DEV_LABEL_ID']])
            if issue['assignee'] is not None:
                issue_card["idMembers"] = self.git_to_trello_assignee_map[issue['assignee']['login']]

            issue_card = trello.post("https://api.trello.com/1/cards", data=issue_card).json()

        return issue_card

    def github_to_trello_sync(self):

        self.fetch_existing_github_state()

        for m, gh_issues in self.grouped_issues:
            # gh_issues = github.get(
            #     "%s/repos/%s/%s/issues" % (github_api, os.environ['REPO_OWNER'], os.environ['REPO_NAME']),
            #     params={"milestone": int(m['number']), "state": "all"}).json()

            if m is None:
                milestone_label = None
            else:
                try:
                    milestone_label = next(
                        label for label in self.existing_milestone_labels
                        if label['name'].endswith('#%s' % m['number']))
                except StopIteration:
                    milestone_label = trello.post("https://api.trello.com/1/labels", data={
                        'name': "%s#%s" % (m['title'], m['number']),
                        'color': 'green',
                        'idBoard': os.environ['TASKS_BOARD_ID']
                    }).json()

            issue_cards = map(lambda issue: self.update_or_create_task_card(
                issue, milestone=m, milestone_label=milestone_label), gh_issues)

            if m is not None:
                if len(issue_cards) == 0:
                    milestone_list_to_use = self.milestones_board_lists['Backlog']
                elif all(card['idList'] == self.tasks_board_lists['Done'] for card in issue_cards):
                    milestone_list_to_use = self.milestones_board_lists['Done']
                elif any(card['idList'] in (
                        self.tasks_board_lists['Doing'],
                        self.tasks_board_lists['Done']) for card in issue_cards):
                    milestone_list_to_use = self.milestones_board_lists['Doing']
                else:
                    milestone_list_to_use = self.milestones_board_lists['To Do']

                members_to_assign = ",".join(
                    list(set(self.git_to_trello_assignee_map[i['assignee']['login']]
                         for i in gh_issues if i['assignee'] is not None
                         and i['assignee']['login'] in self.git_to_trello_assignee_map)))

                try:
                    card = next(card for card in self.existing_milestone_cards
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
                        "idMembers": members_to_assign
                    }
                    if m.get('description') is not None:
                        card['desc'] = m['description'][:16383]
                    trello.post("https://api.trello.com/1/cards", data=card)


def register_milestones_board_trello_hook(hook_server=None):
    if hook_server is None:
        hook_server = os.environ['TRELLOGIT_WEBHOOK']
    callback_url = hook_server + "/milestones"
    trello.post("%s/webhooks" % trello_api, data={
        "description": "Milestone board hook",
        "callbackURL": callback_url,
        "idModel": os.environ['MILESTONES_BOARD_ID']
    })


@app.route('/')
def home():
    record = json.dumps(json.load('record.txt'))
    return render_template("index.html", record=record)


@app.route('/milestones')
def record_milestone_card_action():
    json.dump({
        "headers": request.headers,
        "data": request.get_json()
    }, 'record.txt')
    return Response(jsoned({'status': 'success'}, wrap=False),
                    200, mimetype='application/json')


if __name__ == '__main__':
    syncer = OneTimeSyncer()
    syncer.github_to_trello_sync()

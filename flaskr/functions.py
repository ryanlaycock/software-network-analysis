from datetime import datetime
import project_network
from os import getenv
import requests
import time


def log_time():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def get_project_internal(project_name):
    project = project_network.ProjectNetwork(project_name)
    if not project.project_exists():
        return None
    return project


def post_status_update(project_name, status, msg):
    GATEWAY_URL = getenv("GATEWAY_ADDR")
    print(log_time(), "Posting new status:", status)
    requests.post(GATEWAY_URL + "/projects/" + project_name + "/status", json={
        "status": status,
        "project_name": project_name,
        "msg": msg,
    })


def get_parsing_status(project_name):
    pom_search_service_addr = getenv("POM_SEARCH_SERVICE_ADDR")
    print(log_time(), "Requesting deps state from POM_SEARCH_SERVICE.")
    deps_state_req = requests.get(pom_search_service_addr + '/api/v1/project/' + project_name + '/dependents/state')
    if deps_state_req.status_code == 400 or (
            deps_state_req.status_code == 200 and deps_state_req.json() == {"state": None, "status": "ok"}):
        # Project not found in neo4j or not parsed
        validate_repo = requests.get(pom_search_service_addr + '/api/v1/project/' + project_name + '/validate')
        if validate_repo.status_code == 404 and validate_repo.json()['state'] == 'invalid-repo':
            return "invalid_repo"
        deps_search_obj = {"github_short_url": project_name}
        deps_search = requests.post(pom_search_service_addr + '/api/v1/init/dependents-search/pom',
                                    json=deps_search_obj)
        if deps_search.status_code != 200:
            print(log_time(), "An error occurred with submitting dependents parse job.")
            return "error"
        return "parsing_dependents"
    elif deps_state_req.status_code == 200 and deps_state_req.json() == {"state": "True", "status": "ok"}:
        # Project dependents parsed
        ast_state_req = requests.get(pom_search_service_addr + '/api/v1/ast/' + project_name + '/state')
        if ast_state_req.status_code == 200 and ast_state_req.json() == {"state": "not-parsed", "status": "ok"}:
            ast_search_obj = {"github_short_url": project_name, "parsing_type": "all"}
            ast_search = requests.post(pom_search_service_addr + '/api/v1/init/ast-search/java', json=ast_search_obj)
            if ast_search.status_code != 200:
                print(log_time(), "An error occurred with submitting ast parse job.")
                return "error"
            return "parsing_ast"
        elif ast_state_req.status_code == 200 and ast_state_req.json() == {"state": "in-progress", "status": "ok"}:
            return "ast_parsing_in_progress"
        elif ast_state_req.status_code == 200 and ast_state_req.json() == {"state": "all", "status": "ok"}:
            return "ast_parsed"
        elif ast_state_req.status_code == 200 and ast_state_req.json() == {"state": "queued", "status": "ok"}:
            return "ast_parsing_queued"
        elif ast_state_req.status_code == 200 and ast_state_req.json() == {"state": "failed", "status": "ok"}:
            return "error"
        else:
            return ast_state_req.json()
    else:
        return "dependents_parsing_in_progress"


def compute_metrics(project_name, project):
    project_node = project.get_project_node()
    internal_metrics = project.compute_metrics(project_name, project_node)
    nodes = {}

    for component_id in internal_metrics:
        node = project.graph.nodes(data=True)[component_id]
        if node["type"] == "Project":
            if internal_metrics[component_id]['network_comp'] <= 10000:
                network_comp_msg = "This value indicates the project has a relatively low complexity."
            elif 10000 < internal_metrics[component_id]['network_comp'] <= 70000:
                network_comp_msg = "This value indicates the project has a moderately high complexity."
            else:
                network_comp_msg = "This value indicates the project has a moderately high complexity."

            if internal_metrics[component_id]['code_churn'] <= 100:
                code_churn_msg = "This value indicates the code is infrequently updated, reducing the need for " \
                                   "consistent updates however indicating a risk of outdated and insecure code."
            elif 100 < internal_metrics[component_id]['code_churn'] <= 500:
                code_churn_msg = "This value indicates the code is fairly regularly updated, therefore requiring " \
                                   "dependents to update relatively frequently."
            else:
                code_churn_msg = "This value indicates the project updates frequently, and therefore dependents must " \
                                   "also update frequently to remain in sync."

            nodes["Project"] = {
                "internal_id": component_id,
                "id": node['id'],
                "type": node['type'],
                "code_churn": internal_metrics[component_id]['code_churn'],
                "network_comp": internal_metrics[component_id]['network_comp'],
                "procedure_comp": internal_metrics[component_id]['procedure_comp'],
                "code_churn_msg": code_churn_msg,
                "network_comp_msg": network_comp_msg,
            }
        else:
            if node["type"] == "Method":
                node_obj = {
                    "internal_id": component_id,
                    "id": node['id'],
                    "type": node['type'],
                    "name": node['name'],
                    "network_comp": internal_metrics[component_id]['network_comp'],
                    "procedure_comp": internal_metrics[component_id]['procedure_comp']
                }
            else:
                node_obj = {
                    "internal_id": component_id,
                    "id": node['id'],
                    "type": node['type'],
                    "name": node['name'],
                    "network_comp": internal_metrics[component_id]['network_comp'],
                }
            if node["type"] not in nodes.keys():
                nodes[node["type"]] = []
            nodes[node["type"]].append(node_obj)
    return nodes


def compute_avg_code_change(project_name):
    print(log_time(), "Requesting github code_frequency.")
    req = requests.get("https://api.github.com/repos/" + project_name + "/stats/code_frequency",
                       params={"headers": {"accept": "application/vnd.github.v3+json"}})
    # TODO add api key
    if req.status_code == 200:
        total = 0
        weeks = req.json()
        for week in weeks:
            additions = week[1]
            deletions = week[2]
            total += additions + (-deletions)
        avg = total / len(weeks)
        return avg
    elif req.status_code == 202:  # GitHub processing data
        time.sleep(5)
        return compute_avg_code_change(project_name)
    else:
        print(log_time(), "An error occurred", req.json())
        return 0

import project_network
import dependency_network
from os import getenv
import requests
import time


def get_project_internal(project_name):
    project = project_network.ProjectNetwork(project_name)
    if not project.project_exists():
        return None
    return project


def get_project_dependencies(project_name):
    project = dependency_network.DependencyNetwork(project_name)
    if not project.project_exists():
        return None
    return project


def get_parsing_status(project_name):
    pom_search_service_addr = getenv("POM_SEARCH_SERVICE_ADDR")
    print("requesting deps state")
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
            # TODO Logging here
            print("An error occurred with submitting dependents parse job.")
            return "error"
        return "parsing_dependents"
    elif deps_state_req.status_code == 200 and deps_state_req.json() == {"state": "True", "status": "ok"}:
        # Project dependents parsed
        ast_state_req = requests.get(pom_search_service_addr + '/api/v1/ast/' + project_name + '/state')
        if ast_state_req.status_code == 200 and ast_state_req.json() == {"state": "not-parsed", "status": "ok"}:
            ast_search_obj = {"github_short_url": project_name, "parsing_type": "all"}
            ast_search = requests.post(pom_search_service_addr + '/api/v1/init/ast-search/java', json=ast_search_obj)
            if ast_search.status_code != 200:
                # TODO Logging here
                print("An error occurred with submitting ast parse job.")
                return "error"
            return "parsing_ast"
        elif ast_state_req.status_code == 200 and ast_state_req.json() == {"state": "in-progress", "status": "ok"}:
            return "ast_parsing_in_progress"
        elif ast_state_req.status_code == 200 and ast_state_req.json() == {"state": "all", "status": "ok"}:
            return "ast_parsed"
        elif ast_state_req.status_code == 200 and ast_state_req.json() == {"state": "queued", "status": "ok"}:
            return "ast_parsing_queued"
        else:
            return ast_state_req.json()
    else:
        return "dependents_parsing_in_progress"


def compute_metrics(project_name, project, deps):
    metrics = project.compute_metrics(project_name)
    nodes = {}
    for node in project.graph.nodes(data=True):
        node_obj = {
            "internalId": node[0],
            "id": node[1]['id'],
            "type": node[1]['type'],
            "name": node[1]['name'],
            "metrics": metrics[node[0]]
        }
        if not node[1]["type"] in nodes.keys():
            nodes[node[1]["type"]] = []
        nodes[node[1]["type"]].append(node_obj)
    return nodes


def compute_avg_code_change(project_name):
    print("Requesting github code_frequency")
    req = requests.get("https://api.github.com/repos/" + project_name + "/stats/code_frequency",
                       params={"headers": {"accept": "application/vnd.github.v3+json"}})
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
        print("An error occurred", req.json())
        return 0


def compute_avg_commit_count(project_name):
    print("Requesting github commit count")
    req = requests.get("https://api.github.com/repos/" + project_name + "/stats/participation",
                       params={"headers": {"accept": "application/vnd.github.v3+json"}})
    if req.status_code == 200:
        commits_per_week = req.json()["all"]
        total = sum(commits_per_week)
        avg = total / len(commits_per_week)
        return avg
    elif req.status_code == 202:  # GitHub processing data
        time.sleep(5)
        return compute_avg_commit_count(project_name)
    else:
        print("An error occurred", req.json())
        return 0

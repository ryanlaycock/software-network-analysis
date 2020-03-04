import project_network
from flask import jsonify


def get_project_json(owner, repo, requested_projects):
    """
    Searches the neo4j database for the requested project.
    If found, the data is built into a networkx network and the json is returned to the client
    TODO: If not found
    """
    project_name = owner + "/" + repo
    project = get_project(project_name, requested_projects)
    if project is None:
        return jsonify({"Error": "Project not available."}), 404
    json = project.get_network_json()
    return jsonify(json)


def get_project_stats(owner, repo, requested_projects):
    project_name = owner + "/" + repo
    project = get_project(project_name, requested_projects)
    if project is None:
        return jsonify({"Error": "Project not available."}), 404
    stats = project.get_stats()
    return jsonify(stats)


def get_project(project_name, requested_projects):
    if requested_projects.get(project_name, None) is None:
        project = project_network.ProjectNetwork(project_name)
        if not project.project_exists():
            return None
        requested_projects[project_name] = project
    return requested_projects[project_name]

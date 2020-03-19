import project_network
from flask import jsonify


def get_project_json(owner, repo, requested_projects):
    """
    Searches the neo4j database for the requested project.
    If found, the data is built into a networkx network and the json is returned to the client
    TODO: If not found
    """
    project = get_project(owner, repo, requested_projects)
    if project is None:
        return jsonify({"Error": "Project not available."}), 404
    json = project.get_network_json()
    return jsonify(json)


def get_project_component_graph_json(owner, repo, component, requested_projects):
    project = get_project(owner, repo, requested_projects)
    if project is None:
        return jsonify({"Error": "Project not available."}), 404
    json = project.get_component_network_json(component)
    return jsonify(json)


def get_project_internal_metrics(owner, repo, requested_projects):
    project = get_project(owner, repo, requested_projects)
    if project is None:
        return jsonify({"Error": "Project not available."}), 404
    metrics = project.get_internal_metrics()
    return jsonify(metrics)


def get_project_stats(owner, repo, requested_projects):
    project = get_project(owner, repo, requested_projects)
    if project is None:
        return jsonify({"Error": "Project not available."}), 404
    stats = project.get_stats()
    return jsonify(stats)


def get_project_scc(owner, repo, requested_projects):
    project = get_project(owner, repo, requested_projects)
    scc = project.get_scc()
    return jsonify(scc)


def get_project_degree(owner, repo, limit, graphs, requested_projects):
    project = get_project(owner, repo, requested_projects)
    degree = project.get_degree(limit, graphs)
    return jsonify(degree)


def get_project(owner, repo, requested_projects):
    project_name = owner + "/" + repo
    if requested_projects.get(project_name, None) is None:
        project = project_network.ProjectNetwork(project_name)
        if not project.project_exists():
            return None
        requested_projects[project_name] = project
    return requested_projects[project_name]

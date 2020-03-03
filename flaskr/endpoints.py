import project_network
import json


def get_project(owner, repo, requested_projects, db):
    """
    Searches the neo4j database for the requested project.
    If found, the data is built into a networkx network and the json is returned to the client
    TODO: If not found
    """
    project_name = owner + "/" + repo
    found_network = requested_projects.get(project_name, None)

    if found_network is None:
        network = project_network.ProjectNetwork(project_name)
        if network.project_exists():
            formatted_network = network.get_network_json()
            requested_projects[project_name] = formatted_network
            return json.dumps(formatted_network)
        else:
            return json.dumps("Project not available."), 404
    else:
        return json.dumps(found_network)

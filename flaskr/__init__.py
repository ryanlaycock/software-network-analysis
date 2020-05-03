from flask import Flask, request, jsonify
from flask_cors import CORS
import main
from os import getenv
import requests
import time


def create_app(test_config=None):
    """Flask URL -> endpoints"""
    app = Flask(__name__)
    CORS(app)

    # Routes
    @app.route('/projects/<string:owner>/<string:repo>/valid', methods=['GET'])
    def is_valid(owner, repo):
        pom_search_service_addr = getenv("POM_SEARCH_SERVICE_ADDR")
        project_name = owner + "/" + repo
        validate_repo = requests.get(pom_search_service_addr + '/api/v1/project/' + project_name + '/validate')
        if validate_repo.status_code == 404 and validate_repo.json()['state'] == 'invalid-repo':
            return jsonify({"valid": "false"}), 404
        if validate_repo.status_code == 500:
            return 500
        return jsonify({"valid": "true"}), 200

    @app.route('/projects/<string:owner>/<string:repo>', methods=['GET'])
    def get_project(owner, repo):
        project_name = owner + "/" + repo
        project = main.get_project_from_neo4j(project_name)
        if not project:
            # Project not parsed and in Neo4j
            return jsonify({"state": "not_parsed"}), 404
        else:
            return jsonify(project), 200

    @app.route('/analyse', methods=['POST'])
    def get_project_metrics():
        owner = request.json['owner']
        repo = request.json['repo']
        project_name = owner + "/" + repo
        print("Analyse request for:", project_name)
        if project_name is None:
            print("Project name not set.")
            return jsonify({"error": "an error occurred"}), 500
        status = ""
        last_status = ""
        while status != "error" and status != "ast_parsed":
            status = main.get_parsing_status(project_name)
            if status != last_status:
                main.post_status_update(project_name, status, "Processing project.")
            last_status = status
            time.sleep(5)
        if status == "error":
            return jsonify({"error": "an error occurred attempting to parse this project"}), 500
        if status == "ast_parsed":
            main.post_status_update(project_name, "in_progress", "Fetching project data.")
            project = main.get_project_internal(project_name)
            result = main.compute_metrics(project_name, project)
            return jsonify(result), 200

    return app


if __name__ == '__main__':
    flask_app = create_app()
    flask_app.debug = True
    flask_app.run(host='0.0.0.0', port=5000)

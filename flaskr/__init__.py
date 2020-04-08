from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import graph_db
import endpoints
import project_network
import dependency_network
import main


def create_app(test_config=None):
    """Flask URL -> endpoints"""
    app = Flask(__name__)
    CORS(app)
    requested_projects = {}
    requested_deps = {}

    # Routes
    @app.route('/projects/<string:owner>/<string:repo>/metrics', methods=['GET'])
    def get_project_metrics(owner, repo):
        project_name = owner + "/" + repo

        status = main.get_parsing_status(project_name)
        if status == "error":
            return jsonify({"error": "an error occurred attempting to parse this project"}), 500
        if status == "invalid_repo":
            return jsonify({"error": "invalid project"}), 404
        if status == "ast_parsed":
            project = main.get_project_internal(project_name)
            deps = main.get_project_dependencies(project_name)
            result = main.compute_metrics(project_name, project, deps)
            return jsonify(result), 200
        return jsonify({"status": status}), 202

    def get_project(owner, repo):
        return endpoints.get_project_json(owner, repo, requested_projects)

    @app.route('/owners/<string:owner>/repos/<string:repo>/component/<string:component>/graph')
    def get_project_component_graph(owner, repo, component):
        return endpoints.get_project_component_graph_json(owner, repo, component, requested_projects)

    @app.route('/owners/<string:owner>/repos/<string:repo>/stats')
    def get_project_stats(owner, repo):
        return endpoints.get_project_stats(owner, repo, requested_projects)

    @app.route('/owners/<string:owner>/repos/<string:repo>/scc')
    def get_project_scc(owner, repo):
        return endpoints.get_project_scc(owner, repo, requested_projects)

    @app.route('/owners/<string:owner>/repos/<string:repo>/internal/metrics')
    def get_project_internal_metrics(owner, repo):
        return endpoints.get_project_internal_metrics(owner, repo, requested_projects)

    @app.route('/owners/<string:owner>/repos/<string:repo>/degree')
    def get_project_degree(owner, repo):
        limit = int(request.args.get('limit', default=0))
        graphs = bool(request.args.get('graphs', default=False))
        return endpoints.get_project_degree(owner, repo, limit, graphs, requested_projects)

    # Deps endpoints
    @app.route('/owners/<string:owner>/repos/<string:repo>/deps')
    def get_project_deps(owner, repo):
        # return ""
        return endpoints.get_project_deps_json(owner, repo, requested_deps)

    @app.route('/owners/<string:owner>/repos/<string:repo>/deps/stats')
    def get_project_deps_stats(owner, repo):
        # return ""
        return endpoints.get_project_deps_stats(owner, repo, requested_deps)

    @app.route('/owners/<string:owner>/repos/<string:repo>/deps/metrics')
    def get_project_deps_metrics(owner, repo):
        # return ""
        return endpoints.get_project_deps_metrics(owner, repo, requested_deps)

    return app


if __name__ == '__main__':
    flask_app = create_app()
    flask_app.debug = True
    flask_app.run(host='0.0.0.0', port=5000)

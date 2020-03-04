from flask import Flask
from flask_cors import CORS
import graph_db
import endpoints


def create_app(test_config=None):
    """Flask URL -> endpoints"""
    app = Flask(__name__)
    CORS(app)
    db = graph_db.GraphDb()
    requested_projects = {}

    # Routes
    @app.route('/owners/<string:owner>/repos/<string:repo>')
    def get_project(owner, repo):
        return endpoints.get_project_json(owner, repo, requested_projects)

    @app.route('/owners/<string:owner>/repos/<string:repo>/stats')
    def get_project_stats(owner, repo):
        return endpoints.get_project_stats(owner, repo, requested_projects)

    return app


if __name__ == '__main__':
    flask_app = create_app()
    flask_app.debug = True
    flask_app.run(host='0.0.0.0', port=5000)

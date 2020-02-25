from flask import Flask
import graph_db
import endpoints


def create_app(test_config=None):
    """Flask URL -> endpoints"""
    app = Flask(__name__, instance_relative_config=True)
    db = graph_db.GraphDb()
    requested_projects = {}

    # Routes
    @app.route('/owners/<owner>/repo/<repo>/')
    def get_project(owner, repo):
        return endpoints.get_project(owner, repo, requested_projects, db)

    return app


if __name__ == '__main__':
    flask_app = create_app()
    flask_app.debug = True
    flask_app.run(host='0.0.0.0', port=5000)

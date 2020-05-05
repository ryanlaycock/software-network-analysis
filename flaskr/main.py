from flask import Flask, request, jsonify
from flask_cors import CORS
import functions
from os import getenv
import time

app = Flask(__name__)

"""Flask URL -> endpoints"""
CORS(app)


# Routes
@app.route('/analyse', methods=['POST'])
def get_project_metrics():
    STANDALONE_MODE = getenv("STANDALONE_MODE")
    owner = request.json['owner']
    repo = request.json['repo']
    project_name = owner + "/" + repo
    print(functions.log_time(), "Analyse request for:", project_name)
    if project_name is None:
        print(functions.log_time(), "Project name not set.")
        return jsonify({"error": "an error occurred"}), 500
    status = ""
    last_status = ""

    if STANDALONE_MODE == "True":
        # Standalone mode
        functions.post_status_update(project_name, "in_progress", "Fetching project data.")
        project = functions.get_project_internal(project_name)
        if project.is_empty():
            return jsonify({"error": "standalone mode, project cannot be parsed and is not in the database"}), 503
        result = functions.compute_metrics(project_name, project)
        return jsonify(result), 200
    else:
        while status != "error" and status != "ast_parsed":
            status = functions.get_parsing_status(project_name)
            if status != last_status:
                functions.post_status_update(project_name, status, "Processing project.")
            last_status = status
            time.sleep(5)
        if status == "error":
            return jsonify({"error": "an error occurred attempting to parse this project"}), 500
        if status == "ast_parsed":
            functions.post_status_update(project_name, "in_progress", "Fetching project data.")
            project = functions.get_project_internal(project_name)
            result = functions.compute_metrics(project_name, project)
            return jsonify(result), 200


if __name__ == '__main__':
    print(functions.log_time(), "Starting software network analysis!")
    app.run(host='0.0.0.0', debug=True)

from flask import Flask, request, jsonify
import os

from BpmnParser import *

bpmnParser = BpmnParser()


from config import Config

app = Flask(__name__)
app.config.from_object(Config)


json_dir = "json"
if not os.path.exists(json_dir):
    os.makedirs(json_dir)

shared_dir = "shared"
if not os.path.exists(shared_dir):
    os.makedirs(shared_dir)


@app.route("/", methods=["GET","POST"])
def index():
    if request.method == "GET":
        for filename in os.listdir(shared_dir):
            if filename.endswith(".bpmn"):
                full_path = "shared/"+filename
                parser_output = bpmnParser.process_bpmn(full_path)
                os.remove(full_path)
        data = {"Service Name": app.config["SERVICE_NAME"], "parser_output": parser_output}
        return jsonify(data), 200
    
if __name__ == '__main__':
    app.run(debug=True, host=app.config["HOST_ADDRESS"], port=app.config["HOST_PORT"])
from flask import Flask, request, jsonify
import os

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
        
        data = {"Service Name": app.config["SERVICE_NAME"], "parser_output": True}
        return jsonify(data), 200
    
if __name__ == '__main__':
    app.run(debug=True, host=app.config["HOST_ADDRESS"], port=app.config["HOST_PORT"])
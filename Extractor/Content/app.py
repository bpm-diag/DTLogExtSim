from flask import Flask, request, jsonify
import os
import subprocess

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
    if request.method == "POST":
        files = {
            "xes_file": request.files["xes_file"]
            }
        files["xes_file"].save(files["xes_file"].filename)
        params = {
        "simthreshold": request.form.get("simthreshold", "0.9"),
        "eta": request.form.get("eta", "0.01"),
        "eps": request.form.get("eps", "0.001"),
        }
        print(files)

        cmd = ["python", "main.py",
                "--file", f"{files['xes_file'].filename}", 
                "--output","extractor/",
                "--eta",f"{params['eta']}",
                "--eps",f"{params['eps']}",
                "--simthreshold",f"{params['simthreshold']}"]
        try:
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,  # Keep this for raising exceptions
                universal_newlines=True,
                encoding='utf-8'
            )
            print(process.stdout)  # Print output on success
            data = {"Service Name": app.config["SERVICE_NAME"], "extractor_output": True}
        except subprocess.CalledProcessError as e:
            print(f"-----ERROR-----: Subprocess exited with code {e.returncode}")
            print(e.stderr)  # Print the error output
            data = {"Service Name": app.config["SERVICE_NAME"], "extractor_output": False}

        
        return jsonify(data), 200
    
if __name__ == '__main__':
    app.run(debug=True, host=app.config["HOST_ADDRESS"], port=app.config["HOST_PORT"])
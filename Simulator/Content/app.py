from flask import Flask, request, jsonify
import subprocess
from config import Config

app = Flask(__name__)
app.config.from_object(Config)


@app.route("/", methods=["GET","POST"])
def index():
    if request.method == "POST":
        simulation_path = request.form.get("simulation_path")
        simulation_no_ext = request.form.get("simulation_no_ext")
        scenario_idx = request.form.get("scenario_idx")
        rep_idx = request.form.get("rep_idx")
        try:
            cmd = ["python", "other_main.py", simulation_path, simulation_no_ext, scenario_idx, rep_idx]
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
                return {"Service Name": app.config["SERVICE_NAME"], "parser_output": True}
            except subprocess.CalledProcessError as e:
                print(f"-----ERROR-----: Subprocess exited with code {e.returncode}")
                print(e.stderr)  # Print the error output
                return {"Service Name": app.config["SERVICE_NAME"], "parser_output": False}
        except Exception as e:
            print(f"Error Processing BPMN File: {str(e)}")
            data = {"Service Name": app.config["SERVICE_NAME"], "parser_output": False}
        return jsonify(data), 200
    
if __name__ == '__main__':
    app.run(debug=True, host=app.config["HOST_ADDRESS"], port=app.config["HOST_PORT"])
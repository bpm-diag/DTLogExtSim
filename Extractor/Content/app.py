import os
from flask import Flask, request, jsonify
import uuid
from datetime import datetime


from config import Config
from process_xes_file import ProcessXesFile

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
        
        unique_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        xes_file = request.files["xes_file"]
        new_unique_filename = f"{timestamp}_{xes_file.filename}_{unique_id}"
        print("file stored:",new_unique_filename)
        try:
            xes_file.save(new_unique_filename)

            params = {
            "simthreshold": request.form.get("simthreshold", "0.9"),
            "eta": request.form.get("eta", "0.01"),
            "eps": request.form.get("eps", "0.001"),
            }
            print(params)

            result = ProcessXesFile(file_path=new_unique_filename,
                                    output_dir_path=f"extractor/{unique_id}/",
                                    eta=f"{params['eta']}",
                                    eps=f"{params['eps']}",
                                    simthreshold=f"{params['simthreshold']}"
                                    ).process()
            data = {
                "Service Name": app.config["SERVICE_NAME"],
                "extractor_output": True,
                "result": result
                }
        except Exception as e:
            print(f"Error Processing XES File: {str(e)}")
            data = {
                "Service Name": app.config["SERVICE_NAME"],
                "extractor_output": False,
                "error": str(e)
            }
        finally:
            if os.path.exists(new_unique_filename):
                os.remove(new_unique_filename)
        return jsonify(data), 200
    
if __name__ == '__main__':
    app.run(debug=True, host=app.config["HOST_ADDRESS"], port=app.config["HOST_PORT"])
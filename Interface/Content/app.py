from flask import Flask, render_template, request, send_from_directory, redirect, url_for, jsonify
import os
import zipfile
import xml.etree.ElementTree as ET
import json
import requests
import shutil

from bpmn_parser_module.bpmn_parser import *

from config import Config

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config.from_object(Config)


DOWNLOAD_FOLDER='download'
UPLOAD_FOLDER = 'uploads'
EXTRACTOR_FOLDER = "extractor"
TAG_NAME = "diagbp"

@app.route('/', methods=['GET', 'POST'])
def index():
    for filename in os.listdir(UPLOAD_FOLDER): # remove old log files
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        #remove also folder and files inside it
        if os.path.isdir(file_path):
            shutil.rmtree(file_path)

    for filename in os.listdir(DOWNLOAD_FOLDER): # remove old log files
        file_path = os.path.join(DOWNLOAD_FOLDER, filename)
        os.remove(file_path)
    for filename in os.listdir(EXTRACTOR_FOLDER):
        file_path = os.path.join(EXTRACTOR_FOLDER, filename)
        if os.path.isfile(file_path) or os.path.islink(file_path):  # Delete files and symlinks
            os.remove(file_path)
        elif os.path.isdir(file_path):  # Delete directories
            shutil.rmtree(file_path)
    
    return render_template('index.html')


@app.route("/extractor", methods=["POST"])
def use_extractor():
    """Handles file upload for Extractor."""
    if "xes_file" not in request.files:
        return "No file uploaded", 400

    files = {"xes_file": (request.files["xes_file"].filename, request.files["xes_file"].stream, request.files["xes_file"].mimetype)}
    print(files)
    data = {
        "simthreshold": request.form.get("simthreshold", "0.9"),
        "eta": request.form.get("eta", "0.01"),
        "eps": request.form.get("eps", "0.001"),
    }
    
    try:
        response = requests.post(f"http://{app.config['EXTRACTOR_ADDRESS']}:{app.config['EXTRACTOR_PORT']}/", files=files, data=data)
        return redirect(url_for('extractor_results'))
    except requests.exceptions.RequestException as e:
        return f"Error connecting to Extractor: {str(e)}", 500

@app.route("/simulator", methods=["POST"])
def use_simulator():
    try:
        """Handles file upload for Simulator."""
        if "bpmn_file" not in request.files:
            return "No BPMN file uploaded", 400

        file_bpmn = {"bpmn_file": (request.files["bpmn_file"].filename, request.files["bpmn_file"].stream, request.files["bpmn_file"].mimetype)}
        
        if file_bpmn["bpmn_file"]:
            file_bpmn_no_ext = file_bpmn["bpmn_file"][0].split(".bpmn")[0]
            if os.path.exists(os.path.join(UPLOAD_FOLDER, file_bpmn_no_ext)):
                simulation_path = os.path.join(UPLOAD_FOLDER, file_bpmn_no_ext)
            else:
                os.mkdir(os.path.join(UPLOAD_FOLDER, file_bpmn_no_ext))
                simulation_path = os.path.join(UPLOAD_FOLDER, file_bpmn_no_ext)
            # save bpmn file as .bpmn
            with open(simulation_path + "/" + file_bpmn["bpmn_file"][0], "wb") as f:
                f.write(file_bpmn["bpmn_file"][1].read())

            files_extra = {"extra": (request.files["extra"].filename, request.files["extra"].stream, request.files["extra"].mimetype)} if "extra" in request.files and request.files["extra"].filename != "" else None

            tree = ET.parse(simulation_path + "/" + file_bpmn["bpmn_file"][0])
            root = tree.getroot()
            diagbpTag = root.find('.//' + TAG_NAME)
            if diagbpTag is not None:
                print("DA GESTIRE FOUND DIAGBP")
                # TODO: gestire diagbp
                # probabilmente dovrei prima estrarre dal XML e poi produrre i json necessari 
                # o il json necessario per poi mandarlo il simulator
                # per ora non gestisco
            elif files_extra:
                # TODO: gestire extra
                # probabilmente dovrei estrarre solo il json dal XML
                # e usarlo per mandarlo al simulator
                # per ora non gestisco
                parser = BpmnParser()
                parser_output = parser.process_bpmn(bpmn_path, files_extra)
                if parser_output:
                    with open(bpmn_path+".json", "rb") as f:
                        file_bpmn_json_saved = {"bpmn_file": (file_bpmn["bpmn_file"][0]+".json", f, file_bpmn["bpmn_file"][2])}

                if files_extra:
                    extra_path = os.path.join(UPLOAD_FOLDER, files_extra["extra"][0])
                    with open(extra_path, "wb") as f:
                        f.write(files_extra["extra"][1].read())
                    file_extra_saved = open(extra_path, "rb")
                    files_extra["extra"] = (files_extra["extra"][0], file_extra_saved, files_extra["extra"][2])

                files = {"bpmn_file": file_bpmn["bpmn_file"]}
                if files_extra:
                    files["extra"] = files_extra["extra"]
                    print("DA GESTIRE FOUND EXTRA")
                extra_filename = files_extra["extra"][0] if files_extra and "extra" in files_extra else None
            else:
                print("NESSUN PARAMETRO DI CONFIG")
                parser = BpmnParser()
                parser_output = parser.generate_json_from_bpmn(simulation_path, file_bpmn_no_ext, file_bpmn["bpmn_file"][0])
                if parser_output:
                    print(f"redirecting to parameters with simulation_path: {simulation_path}, simulation_no_ext: {file_bpmn_no_ext}")
                    return redirect(url_for('parameters',
                                simulation_path=simulation_path,
                                simulation_no_ext=file_bpmn_no_ext,
                                flag_extra=0))
                else:
                    return render_template('index.html')

    except OSError as e:
        print("Error saving files: ", e)
        return render_template('index.html')

@app.route('/simulatorResults')
def simulator_results():
    simulation_path = request.args.get('simulation_path')
    return render_template('simulatorResults.html', simulation_path=simulation_path)

@app.route('/extractorResults')
def extractor_results():
    return render_template('extractorResults.html')


@app.route('/parameters', methods=['GET', 'POST'])
def parameters():
    # Get parameters based on request method
    if request.method == 'GET':
        simulation_path = request.args.get('simulation_path')
        simulation_no_ext = request.args.get('simulation_no_ext')
        flag_extra = request.args.get('flag_extra')
    else:  # POST
        simulation_path = request.form.get('simulation_path')
        simulation_no_ext = request.form.get('simulation_no_ext')
        flag_extra = request.form.get('flag_extra')
    
    # Try to read the bpmn_dict file
    bpmn_json_path = os.path.join(simulation_path, simulation_no_ext + ".json")
    with open(bpmn_json_path, 'r') as f:
        bpmn_dict = json.load(f)

    if flag_extra == 1:
        extra_path = os.path.join(simulation_path, "extra.json")
        with open(extra_path, 'r') as f:
            extra = json.load(f)
    
    if request.method == 'POST':
        diagbp_data = {
            "processInstances": [],
            "startDateTime": str(request.form.get('start_date'))+":00",
            "arrivalRateDistribution": {
                "type": request.form.get('inter_arrival_time_type'),  # Convert to lowercase
                "mean": request.form.get('inter_arrival_time_mean'),
                "arg1": request.form.get('inter_arrival_time_arg1'),
                "arg2": request.form.get('inter_arrival_time_arg2'),
                "timeUnit": request.form.get('inter_arrival_time_time_unit'),
            },
            "timetables": [],
            "resources": [],
            "elements": [],
            "sequenceFlows": [],
            "catchEvents": {}
        }

        timetable_data = {}
        for key, value in request.form.items():
            if key.startswith('instance_type_'):
                instance_type = value
                instance_count_key = key.replace('instance_type_', 'instance_count_')
                instance_count = request.form.get(instance_count_key)

                diagbp_data["processInstances"].append({
                    "type": instance_type,
                    "count": instance_count
                })
            elif key.startswith('rule_from_time_'):
                parts = key.split('_')
                timetable_index = int(parts[3])  # Get the timetable index
                rule_index = int(parts[4])        # Get the rule index

                # If the timetable doesn't exist in the dictionary, create it
                if timetable_index not in timetable_data:
                    timetable_data[timetable_index] = {
                        'name': request.form.get(f'timetable_name_{timetable_index}'),
                        'rules': []
                    }

                # Add the rule data to the appropriate timetable
                timetable_data[timetable_index]['rules'].append({
                    "fromTime": str(value)+":00",
                    "toTime": str(request.form.get(f'rule_to_time_{timetable_index}_{rule_index}'))+":00",
                    "fromWeekDay": request.form.get(f'rule_from_day_{timetable_index}_{rule_index}'),
                    "toWeekDay": request.form.get(f'rule_to_day_{timetable_index}_{rule_index}')
                })
            elif key.startswith('resource_name_'):
                resource_index = key.split("_")[2]  # Extract the resource index from the key
                resource_name = value 
                resource_amount = request.form.get(f'resource_amount_{resource_index}')
                resource_cost = request.form.get(f'resource_cost_{resource_index}')
                resource_timetable = request.form.get(f'resource_timetable_{resource_index}')

                setup_time_type = request.form.get(f'resource_{resource_index}_setupTimeType')
                setup_time_mean = request.form.get(f'resource_{resource_index}_setupTimeMean')
                setup_time_arg1 = request.form.get(f'resource_{resource_index}_setupTimeArg1')
                setup_time_arg2 = request.form.get(f'resource_{resource_index}_setupTimeArg2')
                setup_time_unit = request.form.get(f'resource_{resource_index}_setupTimeUnit')
                max_usage = request.form.get(f'resource_maxUsage_{resource_index}')

                if str(setup_time_mean)=="":
                    setup_time_type=""
                    setup_time_unit=""
                
                resource_data = {
                    "name": resource_name,
                    "totalAmount": resource_amount,
                    "costPerHour": resource_cost,
                    "timetableName": resource_timetable,
                    "setupTime": {
                        "type": setup_time_type if setup_time_type else "",
                        "mean": setup_time_mean,
                        "arg1": setup_time_arg1,
                        "arg2": setup_time_arg2,
                        "timeUnit": setup_time_unit
                    },
                    "maxUsage": max_usage
                }
                diagbp_data["resources"].append(resource_data)

        # Now, add the timetables to diagbp_data in the correct order
        diagbp_data["timetables"] = list(timetable_data.values()) 

        nodes_to_process = []
        if 'process_elements' in bpmn_dict:
            for process_id, process_data in bpmn_dict['process_elements'].items():
                nodes_to_process.extend([(node_id, node_data) for node_id, node_data in process_data['node_details'].items()])

        while nodes_to_process:
            node_id, node_data = nodes_to_process.pop(0)
            if node_data['type'] == 'subprocess':
                nodes_to_process.extend([(sub_node_id, sub_node_data) for sub_node_id, sub_node_data in node_data['subprocess_details'].items()])
            elif node_data['type'] == 'task':
                duration_type = request.form.get(f'durationType_{node_id}', 'FIXED')
                duration_mean = request.form.get(f'durationMean_{node_id}', '')
                duration_arg1 = request.form.get(f'durationArg1_{node_id}', '')
                duration_arg2 = request.form.get(f'durationArg2_{node_id}', '')
                duration_time_unit = request.form.get(f'durationTimeUnit_{node_id}', 'seconds')

                duration_threshold = request.form.get(f'durationThreshold_{node_id}', '')
                duration_threshold_time_unit = request.form.get(f'durationThresholdTimeUnit_{node_id}', 'seconds') if duration_threshold else ''

                element_data = {
                        "elementId": node_id,
                        "worklistId": request.form.get(f'worklistId_{node_id}', ''),
                        "fixedCost": request.form.get(f'fixedCost_{node_id}', ''),
                        "costThreshold": request.form.get(f'costThreshold_{node_id}', ''),
                        "durationDistribution": {
                            "type": duration_type,
                            "mean": duration_mean,
                            "arg1": duration_arg1,
                            "arg2": duration_arg2,
                            "timeUnit": duration_time_unit
                        },
                        "durationThreshold": duration_threshold,
                        "durationThresholdTimeUnit": duration_threshold_time_unit,
                        "resourceIds": []
                    }
                i = 1
                while request.form.get(f'resourceName_{i}_{node_id}'):
                    resource_name = request.form.get(f'resourceName_{i}_{node_id}')
                    amount_needed = request.form.get(f'amountNeeded_{i}_{node_id}')
                    group_id = request.form.get(f'groupId_{i}_{node_id}','1')
                    if resource_name and amount_needed:
                            element_data["resourceIds"].append({
                                "resourceName": resource_name,
                                "amountNeeded": amount_needed,
                                "groupId": group_id
                            })
                    i += 1
                diagbp_data["elements"].append(element_data)
            elif node_data['type'] in ['intermediateCatchEvent', 'startEvent'] and \
            node_data.get('subtype') not in ['messageEventDefinition', None]:
                diagbp_data["catchEvents"][node_id] = {
                    "type": request.form.get(f'catchEventDurationType_{node_id}', 'FIXED'),
                    "mean": request.form.get(f'catchEventDurationMean_{node_id}', ''),
                    "arg1": request.form.get(f'catchEventDurationArg1_{node_id}', ''),
                    "arg2": request.form.get(f'catchEventDurationArg2_{node_id}', ''),
                    "timeUnit": request.form.get(f'catchEventDurationTimeUnit_{node_id}', 'seconds')
                }

        if 'sequence_flows' in bpmn_dict:
            for flow_id in bpmn_dict['sequence_flows']:
                execution_probability = request.form.get(f'executionProbability_{flow_id}')
                if execution_probability is None:  # Skip if not provided
                    continue 
                forced_instance_types = []
                i = 1
                while True:
                    forced_instance_type = request.form.get(f'forcedInstanceType_{flow_id}_{i}')
                    if not forced_instance_type:
                        break
                    forced_instance_types.append({"type": forced_instance_type})
                    i += 1

                diagbp_data["sequenceFlows"].append({
                    "elementId": flow_id,
                    "executionProbability": execution_probability,
                    "types": forced_instance_types
                })
            


        # realize the diagbp file corresponding to simulation parameters
        diagbp_data["logging_opt"] = request.form.get('logging_opt', 0)  # Default to 0 (disabled)
        diagbp_json = json.dumps(diagbp_data, indent=4)
        with open(os.path.join(simulation_path, 'extra.json'), 'w') as extra_file:
            extra_file.write(diagbp_json)

        #read the bpmn file
        destination_path = os.path.join(simulation_path, simulation_no_ext + ".bpmn")
        with open(destination_path, 'r') as bpmn_file:
            bpmn_content = bpmn_file.read()

        #insert the diagbp json in the bpmn file
        with open(destination_path, 'w') as file:
            bpmn_content = bpmn_content.replace('</bpmn:definitions>', f'<diagbp>{diagbp_json}</diagbp>\n</bpmn:definitions>')
            file.write(bpmn_content)
        
        values = {"simulation_path": simulation_path,
            "simulation_no_ext": simulation_no_ext}

        try:    
            response = requests.post(f"http://{app.config['SIMULATOR_ADDRESS']}:{app.config['SIMULATOR_PORT']}/", data=values)
            return redirect(url_for('simulator_results', simulation_path=simulation_path))
        except requests.exceptions.RequestException as e:
            print(f"-----ERROR-----: {e}")
            return render_template('index.html')

    if flag_extra:
        return render_template('parameters.html', simulation_path=simulation_path, simulation_no_ext=simulation_no_ext, flag_extra=1, bpmn_dict=bpmn_dict)
    else:
        return render_template('parameters.html', simulation_path=simulation_path, simulation_no_ext=simulation_no_ext, flag_extra=0, bpmn_dict=bpmn_dict)

@app.route('/download_extractor')
def download_extractor():
    # 1. Create the ZIP archive
    zip_filename = 'simulation_logs.zip'
    zip_path = os.path.join(EXTRACTOR_FOLDER, zip_filename)
    if os.path.isfile(zip_path): 
        os.remove(zip_path)
    
    # 3. Create a ZIP archive including subdirectories
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(EXTRACTOR_FOLDER):
            for filename in files:
                file_path = os.path.join(root, filename)
                # Exclude the ZIP file itself
                if file_path == zip_path:
                    continue
                # Preserve directory structure inside ZIP
                archive_name = os.path.relpath(file_path, EXTRACTOR_FOLDER)
                zf.write(file_path, arcname=archive_name)

    # 2. Send the ZIP file for download
    response = send_from_directory(EXTRACTOR_FOLDER, zip_filename, as_attachment=True)

    return response 
   

@app.route('/download_simulator')
def download_simulator():
    simulation_path = request.args.get('simulation_path')
    zip_filename = 'simulation_logs.zip'
    zip_path = os.path.join(simulation_path, zip_filename)
    if os.path.isfile(zip_path): 
        os.remove(zip_path)
    
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for root, _, files in os.walk(simulation_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                # Exclude the ZIP file itself
                if file_path == zip_path:
                    continue
                # Preserve directory structure inside ZIP
                archive_name = os.path.relpath(file_path, simulation_path)
                zf.write(file_path, arcname=archive_name)

    response = send_from_directory(simulation_path, zip_filename, as_attachment=True)

    return response 


@app.errorhandler(404)
def not_found_error(error):
    msg = "Resource not found"
    return jsonify({"error": msg}), 404

@app.errorhandler(400)
def bad_request_error(error):
    return jsonify({"error": "Bad request"}), 400

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(Exception)
def handle_exception(error):
    return jsonify({"error": str(error)}), 500

if __name__ == '__main__':
    app.run(debug=True, host=app.config["HOST_ADDRESS"], port=app.config["HOST_PORT"], use_reloader=True)
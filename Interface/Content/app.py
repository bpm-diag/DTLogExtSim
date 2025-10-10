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

# --- WHATIF: helper per ottenere le ROOT dal servizio whatif_api ---
def _fetch_whatif_roots():
    """
    Chiede a whatif_api la lista di 'root' nel volume uploads condiviso
    (cartelle che contengono almeno un .bpmn e sottocartelle scenario 0,1,2,...).
    """
    try:
        r = requests.get(f"{app.config['WHATIF_API_URL']}/api/uploads/roots", timeout=5)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return []

@app.route('/', methods=['GET', 'POST'])
def index():
    # for filename in os.listdir(UPLOAD_FOLDER): # remove old log files
    #     file_path = os.path.join(UPLOAD_FOLDER, filename)
    #     #remove also folder and files inside it
    #     if os.path.isdir(file_path):
    #         shutil.rmtree(file_path)

    for filename in os.listdir(DOWNLOAD_FOLDER): # remove old log files
        file_path = os.path.join(DOWNLOAD_FOLDER, filename)
        os.remove(file_path)
    for filename in os.listdir(EXTRACTOR_FOLDER):
        file_path = os.path.join(EXTRACTOR_FOLDER, filename)
        if os.path.isfile(file_path) or os.path.islink(file_path):  # Delete files and symlinks
            os.remove(file_path)
        elif os.path.isdir(file_path):  # Delete directories
            shutil.rmtree(file_path)

     # --- WHATIF: passa 'roots' al template per popolare la tendina ---
    roots = _fetch_whatif_roots()
    return render_template('index.html', roots=roots)
    #return render_template('index.html')


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

        number_of_repetitions = int(request.form.get("number_of_repetitions", "1"))

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
                print("FOUND DIAGBP")
                parser = BpmnParser()
                parser_output = parser.generate_json_from_bpmn_diag(simulation_path, file_bpmn_no_ext, file_bpmn["bpmn_file"][0])
                if parser_output:
                    print(f"redirecting to parameters with simulation_path: {simulation_path}, simulation_no_ext: {file_bpmn_no_ext}")
                    return redirect(url_for('parameters',
                                simulation_path=simulation_path,
                                simulation_no_ext=file_bpmn_no_ext,
                                flag_extra=1,
                                number_of_repetitions=number_of_repetitions))
                else:
                    return render_template('index.html')
            elif files_extra:
                print("FOUND EXTRA")
                parser = BpmnParser()
                parser_output = parser.generate_json_from_bpmn(simulation_path, file_bpmn_no_ext, file_bpmn["bpmn_file"][0])
                extra_path = os.path.join(simulation_path, "extra.json")
                with open(extra_path, "wb") as f:
                    f.write(files_extra["extra"][1].read())
                if parser_output:
                    print(f"redirecting to parameters with simulation_path: {simulation_path}, simulation_no_ext: {file_bpmn_no_ext}")
                    return redirect(url_for('parameters',
                                simulation_path=simulation_path,
                                simulation_no_ext=file_bpmn_no_ext,
                                flag_extra=1,
                                number_of_repetitions=number_of_repetitions))
                else:
                    return render_template('index.html')
            else:
                print("NESSUN PARAMETRO DI CONFIG")
                parser = BpmnParser()
                parser_output = parser.generate_json_from_bpmn(simulation_path, file_bpmn_no_ext, file_bpmn["bpmn_file"][0])
                if parser_output:
                    print(f"redirecting to parameters with simulation_path: {simulation_path}, simulation_no_ext: {file_bpmn_no_ext}")
                    return redirect(url_for('parameters',
                                simulation_path=simulation_path,
                                simulation_no_ext=file_bpmn_no_ext,
                                flag_extra=0,
                                number_of_repetitions=number_of_repetitions))
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
        flag_extra = int(request.args.get('flag_extra'))
        number_of_repetitions = int(request.args.get('number_of_repetitions'))
    else:  # POST
        simulation_path = request.form.get('simulation_path')
        simulation_no_ext = request.form.get('simulation_no_ext')
        flag_extra = int(request.form.get('flag_extra'))
        number_of_repetitions = int(request.form.get('number_of_repetitions'))
        number_of_scenarios = int(request.form.get('number_of_scenarios'))

    
    # Try to read the bpmn_dict file
    bpmn_json_path = os.path.join(simulation_path, simulation_no_ext + ".json")
    with open(bpmn_json_path, 'r') as f:
        bpmn_dict = json.load(f)

    if flag_extra == 1:
        extra_path = os.path.join(simulation_path, "extra.json")
        print(extra_path)
        with open(extra_path, 'r') as f:
            extra = json.load(f)
    
    if request.method == 'POST':
        extra_data = {}
        for i in range(number_of_scenarios):
            extra_data[i] = {
                "processInstances": [],
                "startDateTime": str(request.form.get(f'scenario_{i}_start_date'))+":00",
                "arrivalRateDistribution": {
                    "type": request.form.get(f'scenario_{i}_arrival_type'),
                    "mean": request.form.get(f'scenario_{i}_arrival_mean'),
                    "arg1": request.form.get(f'scenario_{i}_arrival_arg1'),
                    "arg2": request.form.get(f'scenario_{i}_arrival_arg2'),
                    "timeUnit": request.form.get(f'scenario_{i}_arrival_time_unit'),
                },
                "timetables": [],
                "resources": [],
                "elements": [],
                "sequenceFlows": [],
                "catchEvents": {}
            }

            timetable_data = {}
            for key, value in request.form.items():
                if key.startswith(f'scenario_{i}_instance_type_'):
                    instance_type = value
                    instance_index = key.split('_')[-1]
                    instance_count_key = f'scenario_{i}_instance_count_{instance_index}'
                    instance_count = request.form.get(instance_count_key)

                    extra_data[i]["processInstances"].append({
                        "type": instance_type,
                        "count": instance_count
                    })
                elif key.startswith(f'scenario_{i}_rule_from_time_'):
                    parts = key.split('_')
                    timetable_index = int(parts[5])  # Get the timetable index
                    rule_index = int(parts[6])        # Get the rule index

                    # If the timetable doesn't exist in the dictionary, create it
                    if timetable_index not in timetable_data:
                        timetable_data[timetable_index] = {
                            'name': request.form.get(f'scenario_{i}_timetable_name_{timetable_index}'),
                            'rules': []
                        }

                    # Add the rule data to the appropriate timetable
                    timetable_data[timetable_index]['rules'].append({
                        "fromTime": str(value)+":00",
                        "toTime": str(request.form.get(f'scenario_{i}_rule_to_time_{timetable_index}_{rule_index}'))+":00",
                        "fromWeekDay": request.form.get(f'scenario_{i}_rule_from_day_{timetable_index}_{rule_index}'),
                        "toWeekDay": request.form.get(f'scenario_{i}_rule_to_day_{timetable_index}_{rule_index}')
                    })
                elif key.startswith(f'scenario_{i}_resource_name_'):
                    resource_index = key.split("_")[4]  # Extract the resource index from the key
                    resource_name = value 
                    resource_amount = request.form.get(f'scenario_{i}_resource_amount_{resource_index}')
                    resource_cost = request.form.get(f'scenario_{i}_resource_cost_{resource_index}')
                    resource_timetable = request.form.get(f'scenario_{i}_resource_timetable_{resource_index}')

                    setup_time_type = request.form.get(f'scenario_{i}_resource_{resource_index}_setupTimeType')
                    setup_time_mean = request.form.get(f'scenario_{i}_resource_{resource_index}_setupTimeMean')
                    setup_time_arg1 = request.form.get(f'scenario_{i}_resource_{resource_index}_setupTimeArg1')
                    setup_time_arg2 = request.form.get(f'scenario_{i}_resource_{resource_index}_setupTimeArg2')
                    setup_time_unit = request.form.get(f'scenario_{i}_resource_{resource_index}_setupTimeUnit')
                    max_usage = request.form.get(f'scenario_{i}_resource_maxUsage_{resource_index}')

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
                    extra_data[i]["resources"].append(resource_data)

            # Now, add the timetables to extra_data[i] in the correct order
            extra_data[i]["timetables"] = list(timetable_data.values()) 

            nodes_to_process = []
            if 'process_elements' in bpmn_dict:
                for process_id, process_data in bpmn_dict['process_elements'].items():
                    nodes_to_process.extend([(node_id, node_data) for node_id, node_data in process_data['node_details'].items()])

            while nodes_to_process:
                node_id, node_data = nodes_to_process.pop(0)
                if node_data['type'] == 'subprocess':
                    nodes_to_process.extend([(sub_node_id, sub_node_data) for sub_node_id, sub_node_data in node_data['subprocess_details'].items()])
                elif node_data['type'] == 'task':
                    duration_type = request.form.get(f'scenario_{i}_durationType_{node_id}', 'FIXED')
                    duration_mean = request.form.get(f'scenario_{i}_durationMean_{node_id}', '')
                    duration_arg1 = request.form.get(f'scenario_{i}_durationArg1_{node_id}', '')
                    duration_arg2 = request.form.get(f'scenario_{i}_durationArg2_{node_id}', '')
                    duration_time_unit = request.form.get(f'scenario_{i}_durationTimeUnit_{node_id}', 'seconds')

                    duration_threshold = request.form.get(f'scenario_{i}_durationThreshold_{node_id}', '')
                    duration_threshold_time_unit = request.form.get(f'scenario_{i}_durationThresholdTimeUnit_{node_id}', 'seconds') if duration_threshold else ''

                    element_data = {
                            "elementId": node_id,
                            "worklistId": request.form.get(f'scenario_{i}_worklistId_{node_id}', ''),
                            "fixedCost": request.form.get(f'scenario_{i}_fixedCost_{node_id}', ''),
                            "costThreshold": request.form.get(f'scenario_{i}_costThreshold_{node_id}', ''),
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
                    resource_idx = 1
                    while request.form.get(f'scenario_{i}_resourceName_{resource_idx}_{node_id}'):
                        resource_name = request.form.get(f'scenario_{i}_resourceName_{resource_idx}_{node_id}')
                        amount_needed = request.form.get(f'scenario_{i}_amountNeeded_{resource_idx}_{node_id}')
                        group_id = request.form.get(f'scenario_{i}_groupId_{resource_idx}_{node_id}','1')
                        if resource_name and amount_needed:
                                element_data["resourceIds"].append({
                                    "resourceName": resource_name,
                                    "amountNeeded": amount_needed,
                                    "groupId": group_id
                                })
                        resource_idx += 1
                    extra_data[i]["elements"].append(element_data)
                elif node_data['type'] in ['intermediateCatchEvent', 'startEvent'] and \
                node_data.get('subtype') not in ['messageEventDefinition', None]:
                    extra_data[i]["catchEvents"][node_id] = {
                        "type": request.form.get(f'scenario_{i}_catchEventDurationType_{node_id}', 'FIXED'),
                        "mean": request.form.get(f'scenario_{i}_catchEventDurationMean_{node_id}', ''),
                        "arg1": request.form.get(f'scenario_{i}_catchEventDurationArg1_{node_id}', ''),
                        "arg2": request.form.get(f'scenario_{i}_catchEventDurationArg2_{node_id}', ''),
                        "timeUnit": request.form.get(f'scenario_{i}_catchEventDurationTimeUnit_{node_id}', 'seconds')
                    }

            if 'sequence_flows' in bpmn_dict:
                for flow_id in bpmn_dict['sequence_flows']:
                    execution_probability = request.form.get(f'executionProbability_{flow_id}')
                    if execution_probability is None:  # Skip if not provided
                        continue 
                    forced_instance_types = []
                    type_idx = 1
                    while True:
                        forced_instance_type = request.form.get(f'forcedInstanceType_{flow_id}_{type_idx}')
                        if not forced_instance_type:
                            break
                        forced_instance_types.append({"type": forced_instance_type})
                        type_idx += 1

                    extra_data[i]["sequenceFlows"].append({
                        "elementId": flow_id,
                        "executionProbability": execution_probability,
                        "types": forced_instance_types
                    })
                


        # realize the diagbp file corresponding to simulation parameters
        extra_data["logging_opt"] = request.form.get('logging_opt', 0)  # Default to 0 (disabled)
        extra_data["number_of_scenarios"] = number_of_scenarios
        extra_data["number_of_repetitions"] = number_of_repetitions


        
        diagbp_json = json.dumps(extra_data, indent=4)
        with open(os.path.join(simulation_path, 'extra.json'), 'w') as extra_file:
            extra_file.write(diagbp_json)
        if flag_extra != 1:
            #read the bpmn file
            destination_path = os.path.join(simulation_path, simulation_no_ext + ".bpmn")
            with open(destination_path, 'r') as bpmn_file:
                bpmn_content = bpmn_file.read()

            #insert the diagbp json in the bpmn file
            with open(destination_path, 'w') as file:
                bpmn_content = bpmn_content.replace('</bpmn:definitions>', f'<diagbp>{diagbp_json}</diagbp>\n</bpmn:definitions>')
                file.write(bpmn_content)
        

        try:
            # Prima di creare la struttura, pulisci le cartelle esistenti
            # Mantieni solo i file nella root del simulation_path
            for item in os.listdir(simulation_path):
                item_path = os.path.join(simulation_path, item)
                # Elimina solo se è una directory
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    print(f"Removed directory: {item_path}")
            # Crea la struttura di cartelle S×R
            for scenario_idx in range(number_of_scenarios):
                scenario_folder = os.path.join(simulation_path, str(scenario_idx))
                os.makedirs(scenario_folder, exist_ok=True)
                
                # Crea le cartelle per le ripetizioni
                for rep_idx in range(number_of_repetitions):
                    repetition_folder = os.path.join(scenario_folder, str(rep_idx))
                    os.makedirs(repetition_folder, exist_ok=True)

                    values = {"simulation_path": simulation_path,
                    "simulation_no_ext": simulation_no_ext,
                    "scenario_idx": scenario_idx,
                    "rep_idx": rep_idx}

                    try:    
                        response = requests.post(f"http://{app.config['SIMULATOR_ADDRESS']}:{app.config['SIMULATOR_PORT']}/", data=values)
                    except requests.exceptions.RequestException as e:
                        print(f"-----ERROR-----: {e}")
                        return render_template('index.html')
            return redirect(url_for('simulator_results', simulation_path=simulation_path))
        except requests.exceptions.RequestException as e:
            print(f"-----ERROR-----: {e}")
            return render_template('index.html')

    if flag_extra == 1:
        return render_template('parameters.html', simulation_path=simulation_path, simulation_no_ext=simulation_no_ext, flag_extra=1, bpmn_dict=bpmn_dict, extra=extra, number_of_repetitions=number_of_repetitions)
    else:
        return render_template('parameters.html', simulation_path=simulation_path, simulation_no_ext=simulation_no_ext, flag_extra=0, bpmn_dict=bpmn_dict, number_of_repetitions=number_of_repetitions)

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

# WHATIF: nuove route per integrazione 
@app.post("/whatif/upload-zip")
def whatif_upload_zip():
    """
    Riceve lo ZIP dal form e lo inoltra a whatif_api per l'estrazione nel volume.
    Accetta i campi:
      - scenario_zip (file .zip)
      - scenario_name (opzionale: nome root di destinazione)
    """
    f = request.files.get("scenario_zip")
    if not f:
        return jsonify({"ok": False, "message": "File ZIP mancante"}), 400

    files = {"scenario_zip": (f.filename, f.stream, f.mimetype or "application/zip")}
    data = {"scenario_name": request.form.get("scenario_name", "")}

    try:
        r = requests.post(f"{app.config['WHATIF_API_URL']}/api/uploads/import-zip",
                          files=files, data=data, timeout=120)
        r.raise_for_status()
        j = r.json()
    except requests.exceptions.RequestException as e:
        app.logger.error(f"/whatif/upload-zip proxy error: {e}")
        return jsonify({"ok": False, "message": "Errore durante upload ZIP"}), 502

    # j contiene: {"ok": True, "root": "<nome_root_creata>"}
    return jsonify({"ok": True, "root": j.get("root")})

@app.get("/whatif/roots")
def whatif_roots():
    """
    Proxy verso whatif_api per ottenere la lista delle root nel volume condiviso.
    Usato dall'index.html via fetch() per popolare/aggiornare il select.
    """
    try:
        r = requests.get(f"{app.config['WHATIF_API_URL']}/api/uploads/roots", timeout=5)
        r.raise_for_status()
        # inoltra la risposta così com'è, come JSON
        return (r.text, r.status_code, {"Content-Type": "application/json"})
    except requests.RequestException as e:
        app.logger.error(f"/whatif/roots proxy error: {e}")
        # in caso di errore, restituisci lista vuota (non bloccare la pagina)
        return jsonify([]), 200

@app.post("/whatif/upload-folder")
def whatif_upload_folder():
    """
    Proxy: riceve una 'cartella' dal browser (input webkitdirectory)
    e la inoltra a whatif_api mantenendo i percorsi relativi (filename).
    """
    files_in = request.files.getlist("files")
    if not files_in:
        return "No files", 400

    # Multipart con più parti 'files'; filename deve rimanere il path relativo
    mp = [("files", (f.filename, f.stream, "application/octet-stream")) for f in files_in]
    data = {}
    if request.form.get("scenario_name"):
        data["scenario"] = request.form.get("scenario_name")

    try:
        r = requests.post(f"{app.config['WHATIF_API_URL']}/api/uploads/import-folder",
                          files=mp, data=data, timeout=300)
        return redirect(url_for('index'))
    except requests.exceptions.RequestException as e:
        return f"Error uploading folder to WhatIf API: {e}", 500

@app.post("/whatif/start")
def whatif_start():
    """
    Legge 'root' e gli scenari selezionati (hidden 'scenarios_csv')
    e redireziona l'utente alla UI di WhatIf con i parametri in querystring.
    """
    from urllib.parse import quote_plus
    root = request.form.get("root", "").strip()
    scenarios_csv = request.form.get("scenarios_csv", "").strip()
    if not root or not scenarios_csv:
        return "Seleziona una root e almeno due scenari.", 400

    # http://localhost:3003?root=<root>&scenarios=0,1,2
    return redirect(f"{app.config['WHATIF_UI_URL']}?root={quote_plus(root)}&scenarios={quote_plus(scenarios_csv)}")


@app.get("/whatif/scenarios")
def whatif_scenarios():
    """
    Ritorna l'elenco delle sottocartelle 'scenario' (0,1,2,...) per la root scelta.
    Proxy verso whatif_api.
    """
    root = request.args.get("root", "")
    if not root:
        return jsonify({"error": "missing root"}), 400
    try:
        r = requests.get(f"{app.config['WHATIF_API_URL']}/api/uploads/scenarios",
                         params={"root": root}, timeout=10)
        return (r.text, r.status_code, r.headers.items())
    except Exception as e:
        app.logger.error(f"/whatif/scenarios proxy error: {e}")
        return jsonify({"error": "proxy error"}), 502

# --- Error Handlers ---
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
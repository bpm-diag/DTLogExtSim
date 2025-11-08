import os, zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import json

from functions import (
    parse_and_clean_dataframe,
    _compute_metrics_for_df,
    aggregate_runs_metrics,
)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:3003","http://127.0.0.1:3003"]}})

UPLOADS_DIR = Path(os.environ.get("UPLOADS_DIR", "/app/uploads"))
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# ---------- helpers ----------
def _safe_rel(p: str) -> Path:
    qp = (UPLOADS_DIR / p).resolve()
    qp.relative_to(UPLOADS_DIR)
    return qp

def _files_in(root: Path, exts: set[str]) -> List[Path]:
    return [p for p in root.iterdir() if p.is_file() and p.suffix.lower() in exts]

def _dirs_in(root: Path) -> List[Path]:
    return [p for p in root.iterdir() if p.is_dir()]

def _is_int_name(p: Path) -> bool:
    try:
        int(p.name); return True
    except: return False

# ---------- discover ----------
@app.get("/api/uploads/roots")
def list_roots():
    roots: List[str] = []
    for child in _dirs_in(UPLOADS_DIR):
        has_bpmn = len(_files_in(child, {".bpmn"})) > 0
        has_scen = any(_is_int_name(d) for d in _dirs_in(child))
        if has_bpmn and has_scen:
            roots.append(child.relative_to(UPLOADS_DIR).as_posix())
    roots.sort()
    return jsonify(roots)

@app.get("/api/uploads/scenarios")
def list_scenarios():
    root = request.args.get("root")
    if not root: return jsonify({"error":"missing root"}), 400
    try: rootp = _safe_rel(root)
    except: return jsonify({"error":"invalid root"}), 400
    if not rootp.exists(): return jsonify({"error":"root not found"}), 404
    scen = [d.name for d in _dirs_in(rootp) if _is_int_name(d)]
    scen.sort(key=lambda x: int(x))
    return jsonify(scen)

# ---------- upload ZIP ----------
@app.post("/api/uploads/import-zip")
def import_zip():
    if "scenario_zip" not in request.files: return jsonify({"error":"missing file"}), 400
    up = request.files["scenario_zip"]
    target = (UPLOADS_DIR / (request.form.get("scenario_name") or Path(up.filename).stem or "scenario"))
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(up.stream) as z: z.extractall(target)
    return jsonify({"ok": True, "root": target.relative_to(UPLOADS_DIR).as_posix()})

# ---------- BPMN dalla root ----------
@app.get("/api/bpmn-from-root")
def bpmn_from_root():
    root = request.args.get("root")
    if not root: return jsonify({"error":"missing root"}), 400
    try: rootp = _safe_rel(root)
    except: return jsonify({"error":"invalid root"}), 400
    if not rootp.exists(): return jsonify({"error":"root not found"}), 404
    bpmn_list = _files_in(rootp, {".bpmn"})
    if not bpmn_list: return jsonify({"error":"no bpmn in root"}), 400
    return send_file(bpmn_list[0], mimetype="text/xml")

# ---------- multi-scenario analyze ----------
def _collect_runs(rootp: Path, scenario_name: str) -> List[Path]:
    scen_dir = rootp / scenario_name
    if not scen_dir.exists(): return []
    runs = [d for d in _dirs_in(scen_dir) if any(p.suffix.lower()==".xes" for p in _files_in(d,{".xes"}))]
    try: runs.sort(key=lambda p: int(p.name))
    except: runs.sort()
    return runs

@app.get("/api/analyze-multi-from-uploads")
def analyze_multi_from_uploads():
    root = request.args.get("root")
    scenarios_csv = request.args.get("scenarios")
    if not root or not scenarios_csv: return jsonify({"error":"missing root or scenarios"}), 400
    try: rootp = _safe_rel(root)
    except: return jsonify({"error":"invalid root"}), 400
    if not rootp.exists(): return jsonify({"error":"root not found"}), 404
    # carica BPMN
    bpmn_files = _files_in(rootp, {".bpmn"})
    if not bpmn_files: return jsonify({"error":"root must contain a .bpmn"}), 400
    bpmn_xml = bpmn_files[0].read_text(encoding="utf-8", errors="ignore")
    
    # carica extra.json dalla root se presente ***
    extra_path = rootp / "extra.json"
    extra_all = None
    if extra_path.exists():
        try:
            with open(extra_path, "r", encoding="utf-8") as f:
                extra_all = json.load(f)
        except Exception:
            extra_all = None
    scenarios = [s.strip() for s in scenarios_csv.split(",") if s.strip()!=""]
    if len(scenarios) < 1:
        return jsonify({"error":"select at least one scenario"}), 400

    out: Dict[str, Any] = {}
    for scen in scenarios:
        runs = _collect_runs(rootp, scen)
        per_run_metrics: List[Dict[str, Any]] = []

        # estrae il blocco extra dello scenario (string->dict); se non c'è, None
        extra_scenario = None
        if extra_all is not None:
            # extra.json potrebbe usare chiavi intere o stringhe; normalizza a stringa
            if scen in extra_all:
                extra_scenario = extra_all.get(scen)
            elif scen.isdigit() and int(scen) in extra_all:
                extra_scenario = extra_all.get(int(scen))

        for rdir in runs:
            for x in _files_in(rdir, {".xes"}):
                xes_xml = x.read_text(encoding="utf-8", errors="ignore")
                df = parse_and_clean_dataframe(xes_xml)
                per_run_metrics.append(_compute_metrics_for_df(df, bpmn_xml=bpmn_xml, extra_scenario=extra_scenario))
        if per_run_metrics:
            out[scen] = per_run_metrics[0] if len(per_run_metrics)==1 else aggregate_runs_metrics(per_run_metrics)

    if not out: return jsonify({"error":"no metrics computed"}), 400
    return jsonify({"root": root, "scenario_order": [s for s in scenarios if s in out], "scenarios": out})

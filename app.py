"""
app.py

A multi-endpoint, job-based Flask application to handle EnergyPlus workflows.

Endpoints:
  1) POST /jobs
     - Receives a combined JSON payload (like 'combined.json'),
       creates a new job with a unique job_id,
       splits the JSON into separate files (e.g., main_config.json, fenestration.json, etc.)
       in user_configs/<job_id>.
       Also creates an output subfolder output/<job_id>.
       Stores these paths in the job config.

  2) POST /jobs/<job_id>/start
     - Enqueues the job for execution (runs orchestrate_workflow in a background thread).

  3) GET /jobs/<job_id>/logs
     - Streams the logs in real time from the job_manager's log queue.

  4) POST /jobs/<job_id>/cancel
     - Attempts to cancel the job (if queued or running).

  5) GET /jobs/<job_id>/status
     - Returns the current status: CREATED, QUEUED, RUNNING, FINISHED, ERROR, or CANCELED.

  6) GET /jobs/<job_id>/results
     - Example endpoint to list or fetch final simulation results in output/<job_id>,
       or you can adapt to zip & return them. 
"""

import logging
import os

from flask import Flask, request, Response, jsonify

# ------------------------------------------------------------------------
# Import the job manager for concurrency, queue-based logs, etc.
# ------------------------------------------------------------------------
from job_manager import (
    create_job,
    enqueue_job,
    get_job,
    get_job_logs_queue,
    get_job_status,
    cancel_job
)

# ------------------------------------------------------------------------
# Import the splitter to break the combined JSON into sub-files
# ------------------------------------------------------------------------
from splitter import split_combined_json

###############################################################################
# Flask Application
###############################################################################
app = Flask(__name__)

###############################################################################
# 1) CREATE JOB - POST /jobs
###############################################################################
@app.route("/jobs", methods=["POST"])
def create_job_endpoint():
    """
    Accepts a JSON payload describing the entire workflow config (similar to 'combined.json').
    
    Steps performed:
      - Generate a new job_id (status=CREATED).
      - Create a subfolder for user_configs/<job_id> for the input config files.
      - Create a subfolder for output/<job_id> for the simulation results.
      - Split the posted JSON into multiple config files (e.g., main_config.json).
      - Store these paths in the job's config.
    
    Returns:
      JSON response: { "job_id": "<unique-uuid>" }
    """
    if not request.is_json:
        return jsonify({"error": "Expected JSON payload"}), 400

    # 1) Load the combined JSON from request
    posted_data = request.get_json()

    # 2) Create a job with an initially empty config
    job_id = create_job(config={})  
    # Note: create_job() sets job["config"]["job_id"] = job_id internally.

    # 3) Create a subfolder for user_configs/<job_id>
    #    This ensures concurrency-friendly isolation (no overwriting each other's files).
    base_user_configs = os.path.join(os.getcwd(), "user_configs")
    job_subfolder = os.path.join(base_user_configs, job_id)
    os.makedirs(job_subfolder, exist_ok=True)

    # 4) Create a corresponding output folder for this job's results: output/<job_id>
    base_output = os.path.join(os.getcwd(), "output")
    job_output_folder = os.path.join(base_output, job_id)
    os.makedirs(job_output_folder, exist_ok=True)

    # 5) Split the combined JSON into multiple files, each named <top_key>.json
    split_combined_json(posted_data, job_subfolder)

    # 6) Update the job config with the subfolder paths
    new_config = {
        # job_id is already stored, but you can re-store it if you want:
        "job_id": job_id,
        "job_subfolder": job_subfolder,
        "output_subfolder": job_output_folder,
        "posted_data": posted_data
    }

    job = get_job(job_id)
    if job:
        job["config"] = new_config

    # 7) Return the job_id so the user can call /jobs/<job_id>/start
    return jsonify({"job_id": job_id}), 200


###############################################################################
# 2) START JOB - POST /jobs/<job_id>/start
###############################################################################
@app.route("/jobs/<job_id>/start", methods=["POST"])
def start_job(job_id):
    """
    Moves the job from CREATED => RUNNING (or QUEUED if concurrency is max).
    The job_manager enqueue_job() will handle concurrency checks.

    Response:
      {
        "message": "Job enqueued or running",
        "job_id": "<the job_id>"
      }
    """
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "No such job_id"}), 404

    # Enqueue or start the job
    enqueue_job(job_id)

    return jsonify({"message": "Job enqueued or running", "job_id": job_id}), 200


###############################################################################
# 3) STREAM LOGS - GET /jobs/<job_id>/logs
###############################################################################
@app.route("/jobs/<job_id>/logs", methods=["GET"])
def get_job_logs(job_id):
    """
    Streams the logs in real time from the job's log queue.
    The job_manager signals end of logs by sending a 'None' sentinel.

    Usage Example (PowerShell):
      curl.exe http://localhost:8000/jobs/<job_id>/logs
    """
    log_queue = get_job_logs_queue(job_id)
    if not log_queue:
        return jsonify({"error": "No such job or no logs queue"}), 404

    def log_stream():
        while True:
            line = log_queue.get()
            if line is None:
                break
            yield line + "\n"

    return Response(log_stream(), mimetype="text/plain")


###############################################################################
# 4) CANCEL JOB - POST /jobs/<job_id>/cancel
###############################################################################
@app.route("/jobs/<job_id>/cancel", methods=["POST"])
def cancel_job_endpoint(job_id):
    """
    Attempts to cancel the job:
      - If QUEUED, remove from queue -> status=CANCELED
      - If RUNNING, set cancel_event -> orchestrator can gracefully stop if it checks for cancellations
      - If FINISHED/ERROR/CANCELED, no effect

    Response:
      { "message": "Job <job_id> canceled" } or { "error": ... }
    """
    success = cancel_job(job_id)
    if success:
        return jsonify({"message": f"Job {job_id} canceled"}), 200
    else:
        return jsonify({"error": "Could not cancel (job not found or already finished/canceled)"}), 400


###############################################################################
# 5) JOB STATUS - GET /jobs/<job_id>/status
###############################################################################
@app.route("/jobs/<job_id>/status", methods=["GET"])
def get_job_status_endpoint(job_id):
    """
    Returns the current status of the job:
      - CREATED
      - QUEUED
      - RUNNING
      - FINISHED
      - ERROR
      - CANCELED

    Response:
      {
        "job_id": "<job_id>",
        "status": "<STATUS>"
      }
    """
    status = get_job_status(job_id)
    if status is None:
        return jsonify({"error": "No such job_id"}), 404

    return jsonify({"job_id": job_id, "status": status}), 200


###############################################################################
# 6) GET /jobs/<job_id>/results
###############################################################################
@app.route("/jobs/<job_id>/results", methods=["GET"])
def get_job_results(job_id):
    """
    (Placeholder endpoint)
    If your orchestrator or IDF creation writes final outputs to 
    output/<job_id> (or some subfolder), you can retrieve or list them here.
    
    Example usage:
      - Check existence of job config to get "output_subfolder".
      - Possibly zip the folder or return direct file.
    """
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "No such job"}), 404

    cfg = job["config"]
    out_dir = cfg.get("output_subfolder")
    if not out_dir or not os.path.exists(out_dir):
        return jsonify({"error": f"No results found for job {job_id}"}), 404

    # For now, just respond with a simple message:
    return jsonify({
        "message": f"Results directory is: {out_dir} (Implement your own listing or zip download)."
    }), 200


###############################################################################
# MAIN - For local dev
###############################################################################
if __name__ == "__main__":
    """
    In local dev, run Flask directly:
      python app.py

    For production usage, it's recommended to run:
      gunicorn -b 0.0.0.0:8000 app:app --workers=4
    from your Dockerfile or docker-compose.
    """
    app.run(host="0.0.0.0", port=8000, debug=True)

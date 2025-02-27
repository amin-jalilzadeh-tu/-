"""
app.py

A multi-endpoint, job-based Flask application to handle EnergyPlus workflows.

Endpoints:
  1) POST /jobs
     - Receives a combined JSON payload (like 'combined.json'),
       creates a new job with a unique job_id,
       splits the JSON into separate files (e.g., main_config.json, fenestration.json, etc.)
       in user_configs/<job_id>.

  2) POST /jobs/<job_id>/start
     - Enqueues the job for execution (runs orchestrate_workflow in a background thread).

  3) GET /jobs/<job_id>/logs
     - Streams the logs in real time from the job_manager's log queue.

  4) POST /jobs/<job_id>/cancel
     - Attempts to cancel the job (if queued or running).

  5) GET /jobs/<job_id>/status
     - Returns the current status: CREATED, QUEUED, RUNNING, FINISHED, ERROR, or CANCELED.

  6) GET /jobs/<job_id>/results (Optional)
     - Example endpoint to retrieve or reference final simulation results.

Usage Flow:
  - Client POSTs the combined JSON to /jobs -> gets {"job_id":"<uuid>"}.
  - Then POST /jobs/<uuid>/start to run it.
  - Optionally GET /jobs/<uuid>/logs to see progress, or /jobs/<uuid>/status to poll.
  - Results can be retrieved once the job is FINISHED.
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
      - Create a subfolder for this job: user_configs/<job_id>.
      - Split the posted JSON into main_config.json, dhw.json, etc. in that subfolder.
      - Store the subfolder path (and optionally the original posted data) in the job's config.
    
    Returns:
      JSON response: { "job_id": "<unique-uuid>" }
    """
    if not request.is_json:
        return jsonify({"error": "Expected JSON payload"}), 400

    # 1) Load the combined JSON from request
    posted_data = request.get_json()

    # 2) Create a job with an initially empty config
    job_id = create_job(config={})

    # 3) Create a subfolder for user_configs/<job_id>
    #    This ensures concurrency-friendly isolation (no overwriting each other's files).
    base_user_configs = os.path.join(os.getcwd(), "user_configs")
    job_subfolder = os.path.join(base_user_configs, job_id)
    os.makedirs(job_subfolder, exist_ok=True)

    # 4) Split the combined JSON into multiple files, each named <top_key>.json
    #    e.g. main_config.json, fenestration.json, etc.
    split_combined_json(posted_data, job_subfolder)

    # 5) Update the job's config to store:
    #    - The subfolder path (so orchestrator knows where to read main_config.json).
    #    - Possibly the entire posted_data for reference if you want it later.
    new_config = {
        "job_subfolder": job_subfolder,
        "posted_data": posted_data
    }

    # 6) Store this config in the job dictionary
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
# 6) OPTIONAL: GET /jobs/<job_id>/results
###############################################################################
@app.route("/jobs/<job_id>/results", methods=["GET"])
def get_job_results(job_id):
    """
    (Placeholder endpoint)
    If your orchestrator writes final CSV or other files to e.g. output/Sim_Results/<job_id>,
    you can retrieve or list them here.

    Example:
      1) Confirm the folder exists
      2) Possibly zip and return a download link or direct file
    """
    results_dir = f"output/Sim_Results/{job_id}"
    if not os.path.exists(results_dir):
        return jsonify({"error": "No results found for that job"}), 404

    return jsonify({"message": f"Results directory is {results_dir}. (Implement your own download logic)"})


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

"""
job_manager.py

A more comprehensive in-memory job manager to handle multiple
workflow runs (jobs). Each job can be in states like CREATED,
QUEUED, RUNNING, FINISHED, ERROR, or CANCELED.

Features:
  - Unique job_id generation
  - Concurrency limit (max simultaneous running jobs)
  - Job queue (if concurrency limit is reached)
  - In-memory log queue for real-time streaming
  - Support for cancellation
  - Placeholders for persistence (if needed in future)

CAVEATS:
  - If the Python process exits, in-memory jobs are lost.
  - For production usage, consider a persistent store (Redis, DB).
"""

import uuid
import queue
import threading
import time
import enum
from typing import Any, Dict, Optional, Union

from orchestrator import WorkflowCanceled


###############################################################################
# Global Job Store and Concurrency
###############################################################################

# You can store up to X jobs as RUNNING at once. Others will wait in a queue.
MAX_RUNNING_JOBS = 2

# The global store for jobs and a global queue for waiting jobs.
_jobs: Dict[str, Dict] = {}
_waiting_jobs: queue.Queue = queue.Queue()  # For jobs awaiting execution if concurrency is at max.

# A global lock to protect shared state, e.g., reading/writing _jobs, counting running jobs, etc.
_jobs_lock = threading.Lock()

###############################################################################
# Enum: JobStatus
###############################################################################
class JobStatus(str, enum.Enum):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    ERROR = "ERROR"
    CANCELED = "CANCELED"


###############################################################################
# Data Structure for Each Job
###############################################################################
# Each job dictionary in _jobs has keys:
#   {
#       "status": JobStatus,
#       "config": dict,             # includes "job_id" and other user config
#       "logs": queue.Queue,        # For log streaming
#       "thread": threading.Thread or None,
#       "result": Any,              # Store final result or summary
#       "cancel_event": threading.Event # Signals that we want to cancel
#   }


###############################################################################
# Main API
###############################################################################

def create_job(config: dict) -> str:
    """
    Create a new job, store it in _jobs, return its job_id.
    
    :param config: Dictionary of user-supplied config for the job
    :return: job_id (string)
    """
    job_id = str(uuid.uuid4())
    with _jobs_lock:
        # We also store job_id in the config so orchestrator can see it.
        config["job_id"] = job_id

        _jobs[job_id] = {
            "status": JobStatus.CREATED,
            "config": config,
            "logs": queue.Queue(),
            "thread": None,
            "result": None,
            "cancel_event": threading.Event(),
        }
    return job_id


def enqueue_job(job_id: str) -> None:
    """
    Place a job into the waiting queue if concurrency is at max, or run it immediately if not.
    """
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return
        # If job is not in CREATED state, do nothing
        if job["status"] != JobStatus.CREATED:
            return

        # Count how many are running
        running_count = sum(1 for j in _jobs.values() if j["status"] == JobStatus.RUNNING)
        if running_count < MAX_RUNNING_JOBS:
            # We can start this job immediately
            _start_job(job_id)
        else:
            # We have to queue it
            job["status"] = JobStatus.QUEUED
            _waiting_jobs.put(job_id)


def get_job(job_id: str) -> Optional[Dict]:
    """Retrieve the entire job dictionary by job_id."""
    with _jobs_lock:
        return _jobs.get(job_id)


def get_job_status(job_id: str) -> Optional[str]:
    """Return the status of the job as a string (or None if not found)."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job:
            return job["status"]
    return None


def get_job_logs_queue(job_id: str) -> Optional[queue.Queue]:
    """Return the logs queue for a job, if it exists."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job:
            return job["logs"]
    return None


def cancel_job(job_id: str) -> bool:
    """
    Signal that a job should be canceled (if RUNNING or QUEUED).
    This sets the 'cancel_event' so the job's thread can check and stop if possible.
    
    :return: True if job was canceled or is in the process of being canceled, False if not found.
    """
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return False

        status = job["status"]
        if status in [JobStatus.FINISHED, JobStatus.ERROR, JobStatus.CANCELED]:
            return False  # It's already done or canceled

        # Signal the thread to stop
        job["cancel_event"].set()

        if status == JobStatus.QUEUED:
            # If queued, remove it from the queue
            # We'll need to rebuild the queue without that job_id
            _remove_queued_job(job_id)
            job["status"] = JobStatus.CANCELED
        elif status == JobStatus.RUNNING:
            # The thread should eventually notice the cancel_event
            pass
        else:
            # If CREATED and not yet enqueued, we'll just mark it canceled
            if status == JobStatus.CREATED:
                job["status"] = JobStatus.CANCELED

        return True


def set_job_result(job_id: str, result_data: Any) -> None:
    """Store final results or summary data for the given job."""
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id]["result"] = result_data


def get_job_result(job_id: str) -> Any:
    """Retrieve whatever was set as the result data."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job:
            return job["result"]
    return None


###############################################################################
# Internal Worker Helpers
###############################################################################

def _start_job(job_id: str) -> None:
    """
    Transition job to RUNNING and spawn a thread to execute it.
    """
    job = _jobs[job_id]
    job["status"] = JobStatus.RUNNING

    # We'll create a new thread that calls _job_thread_runner(job_id)
    t = threading.Thread(target=_job_thread_runner, args=(job_id,), daemon=True)
    job["thread"] = t
    t.start()


def _job_thread_runner(job_id: str) -> None:
    """Worker function that runs in a separate thread for each job."""
    try:
        job = _jobs[job_id]
        cancel_event = job["cancel_event"]

        # 1) Import orchestrate_workflow
        from orchestrator import orchestrate_workflow

        # 2) Run the workflow, passing the entire job["config"] which has "job_id"
        orchestrate_workflow(job["config"], cancel_event=cancel_event)

        # If orchestrate_workflow finishes with no exception => FINISHED
        job["status"] = JobStatus.FINISHED

    except WorkflowCanceled:
        job["status"] = JobStatus.CANCELED
    except Exception as e:
        job["status"] = JobStatus.ERROR
        err_msg = f"[Job {job_id}] crashed => {e}"
        job["logs"].put(err_msg)
    finally:
        _signal_end_of_logs(job_id)
        _try_start_next_queued_job()


def _try_start_next_queued_job():
    """
    Check if there's a queued job. If concurrency allows, start it.
    """
    with _jobs_lock:
        running_count = sum(1 for j in _jobs.values() if j["status"] == JobStatus.RUNNING)
        if running_count >= MAX_RUNNING_JOBS:
            return  # No slot available

        # Otherwise, pop from waiting queue if any
        while not _waiting_jobs.empty():
            next_job_id = _waiting_jobs.get()
            job = _jobs.get(next_job_id)
            if not job:
                continue  # might have been canceled or removed

            if job["status"] == JobStatus.QUEUED:
                # Start it
                _start_job(next_job_id)
                break


def _remove_queued_job(job_id: str):
    """
    Remove a job from the waiting queue if it's in there by rebuilding the queue 
    without that job_id.
    """
    temp_list = []
    while not _waiting_jobs.empty():
        j_id = _waiting_jobs.get()
        if j_id != job_id:
            temp_list.append(j_id)
    # re-queue the others
    for j_id in temp_list:
        _waiting_jobs.put(j_id)


def _signal_end_of_logs(job_id: str):
    """
    Put a `None` sentinel in the job's log queue to indicate no more logs.
    The client log streamer can break on encountering None.
    """
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job:
            job["logs"].put(None)

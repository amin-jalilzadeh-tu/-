"""
orchestrator/utils.py

Common utilities used across all orchestrator modules.
"""

import os
import time
import logging
import threading
from contextlib import contextmanager
from typing import Optional


class WorkflowCanceled(Exception):
    """Custom exception used to stop the workflow if a cancel_event is set."""
    pass


def check_canceled(cancel_event: Optional[threading.Event], logger: logging.Logger) -> None:
    """
    Check if workflow has been canceled and raise exception if so.
    
    Args:
        cancel_event: Threading event that signals cancellation
        logger: Logger instance
        
    Raises:
        WorkflowCanceled: If cancel_event is set
    """
    if cancel_event and cancel_event.is_set():
        logger.warning("=== CANCEL event detected. Stopping workflow. ===")
        raise WorkflowCanceled("Workflow was canceled by user request.")


@contextmanager
def step_timer(logger: logging.Logger, name: str):
    """
    Context manager to log step durations.
    
    Args:
        logger: Logger instance
        name: Name of the step being timed
    """
    logger.info(f"[STEP] Starting {name} ...")
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.info(f"[STEP] Finished {name} in {elapsed:.2f} seconds.")


def patch_if_relative(csv_path: str, job_output_dir: str) -> str:
    """
    Convert relative paths to absolute paths within job output directory.
    
    Rules:
    1) If absolute, return as-is.
    2) If starts with 'data/', interpret as /usr/src/app/data/... (no job folder).
    3) Else, join with job_output_dir.
    
    Args:
        csv_path: Path to convert
        job_output_dir: Job output directory
        
    Returns:
        Absolute path
    """
    if not csv_path:
        return csv_path
    
    # Normalize path separators for cross-platform compatibility
    csv_path = csv_path.replace('\\', '/')
    
    if os.path.isabs(csv_path):
        return csv_path
    if csv_path.startswith("data/"):
        return os.path.join("/usr/src/app", csv_path)
    return os.path.join(job_output_dir, csv_path)


def patch_paths_in_config(config: dict, job_output_dir: str, path_keys: list) -> None:
    """
    Patch multiple paths in a configuration dictionary in-place.
    
    Args:
        config: Configuration dictionary to modify
        job_output_dir: Job output directory
        path_keys: List of keys in config that contain paths
    """
    for key in path_keys:
        if key in config and config[key]:
            config[key] = patch_if_relative(config[key], job_output_dir)
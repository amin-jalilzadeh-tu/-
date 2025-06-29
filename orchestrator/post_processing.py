"""
orchestrator/post_processing.py

Post-processing logic including zip, email, cleanup, and structuring.
"""

import os
import json
import logging
from typing import Optional

from zip_and_mail import zip_user_output, send_results_email
from cleanup_old_jobs import cleanup_old_results


def run_post_processing(
    user_configs_folder: str,
    job_output_dir: str,
    logger: logging.Logger
) -> None:
    """
    Run post-processing tasks including zip and email.
    """
    try:
        mail_user_path = os.path.join(user_configs_folder, "mail_user.json")
        mail_info = {}
        
        if os.path.isfile(mail_user_path):
            with open(mail_user_path, "r") as f:
                mail_info = json.load(f)

            mail_user_list = mail_info.get("mail_user", [])
            if len(mail_user_list) > 0:
                first_user = mail_user_list[0]
                recipient_email = first_user.get("email", "")
                if recipient_email:
                    zip_path = zip_user_output(job_output_dir)
                    send_results_email(zip_path, recipient_email)
                    logger.info(f"[INFO] Emailed zip {zip_path} to {recipient_email}")
                else:
                    logger.warning("[WARN] mail_user.json => missing 'email'")
            else:
                logger.warning("[WARN] mail_user.json => 'mail_user' list is empty.")
        else:
            logger.info("[INFO] No mail_user.json found, skipping email.")
            
    except Exception as e:
        logger.error(f"[ERROR] Zipping/Emailing results failed => {e}")


def cleanup_old_results_safe(logger: logging.Logger) -> None:
    """
    Safely run cleanup of old job folders.
    """
    try:
        cleanup_old_results()  # This will remove any job folder older than MAX_AGE_HOURS
    except Exception as e:
        logger.error(f"[CLEANUP ERROR] => {e}")
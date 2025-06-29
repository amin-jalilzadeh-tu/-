"""
zip_and_mail.py

Provides functions to:
  1) Zip an output directory for a particular job_id.
  2) Send an email with that zip file as an attachment, using SMTP settings from .env.
"""

import os
import shutil
import smtplib
import ssl
from email.message import EmailMessage

def zip_user_output(job_output_dir: str) -> str:
    """
    Zips everything (files/folders) inside 'job_output_dir' into a single .zip file.

    Returns the absolute path to the created .zip file.

    Example usage:
        zip_path = zip_user_output("/usr/src/app/output/1a2b3c-job")
        # => "/usr/src/app/output/1a2b3c-job_results.zip"
    """
    # The base name of the directory. e.g. if job_output_dir="/usr/src/app/output/<job_id>"
    # then base_name might be "<job_id>".
    job_folder_name = os.path.basename(job_output_dir.rstrip("/\\"))
    parent_dir      = os.path.dirname(job_output_dir.rstrip("/\\"))

    # We want the zipfile to appear in the same parent directory or wherever you prefer.
    # e.g. /usr/src/app/output/<job_id>_results.zip
    zip_filename = f"{job_folder_name}_results"   # no extension yet
    zip_fullpath_no_ext = os.path.join(parent_dir, zip_filename)  # e.g. /usr/src/app/output/<job_id>_results

    # shutil.make_archive() automatically appends ".zip" if format='zip'.
    # So the final zip file is "/usr/src/app/output/<job_id>_results.zip"
    shutil.make_archive(
        base_name=zip_fullpath_no_ext,
        format='zip',
        root_dir=job_output_dir
    )

    # The final zipped file is the above path + ".zip".
    final_zip_path = zip_fullpath_no_ext + ".zip"
    return final_zip_path

def send_results_email(zip_file: str, recipient_email: str):
    """
    Emails the given zip file to recipient_email using SMTP settings from environment variables.

    Expects the following env variables (for example):
      SMTP_SERVER      - e.g. 'smtp.gmail.com'
      SMTP_PORT        - e.g. '465' or '587' etc
      SMTP_USERNAME    - e.g. your email or login
      SMTP_PASSWORD    - your email password / app password
      MAIL_SENDER      - the 'From:' address
    """
    smtp_server   = os.getenv('SMTP_SERVER',   'localhost')
    smtp_port     = int(os.getenv('SMTP_PORT', '25'))
    smtp_user     = os.getenv('SMTP_USERNAME', None)
    smtp_password = os.getenv('SMTP_PASSWORD', None)
    mail_sender   = os.getenv('MAIL_SENDER',   'noreply@example.com')

    # Create the email
    msg = EmailMessage()
    msg['Subject'] = "Your EnergyPlus Simulation Results"
    msg['From']    = mail_sender
    msg['To']      = recipient_email
    msg.set_content("Hello,\n\nAttached are your EnergyPlus simulation results.\n\nRegards,\nThe Team")

    # Attach the zip file
    with open(zip_file, 'rb') as f:
        zip_data = f.read()
    msg.add_attachment(zip_data,
                       maintype='application',
                       subtype='zip',
                       filename=os.path.basename(zip_file))

    # Optionally you can do SSL or STARTTLS. Here is an SSL example:
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as smtp:
        if smtp_user and smtp_password:
            smtp.login(smtp_user, smtp_password)
        smtp.send_message(msg)

    print(f"[INFO] Sent email with results to {recipient_email} containing {zip_file}")

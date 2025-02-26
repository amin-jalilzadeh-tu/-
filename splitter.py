import os
import json
import logging

def split_combined_json(posted_data, output_folder):
    """
    Splits one combined dict (which might have keys like 'dhw', 'epw', 'fenestration',
    'geometry', 'hvac', 'lighting', 'main_config', 'shading', 'vent') into separate
    JSON files in output_folder.

    Args:
        posted_data (dict): The combined data from the user (already loaded as JSON).
        output_folder (str): e.g. 'user_configs'
    """
    logger = logging.getLogger(__name__)
    os.makedirs(output_folder, exist_ok=True)

    # Loop over top-level keys in posted_data
    for top_key, value in posted_data.items():
        # e.g., if top_key == 'dhw', then we want 'dhw.json'
        out_path = os.path.join(output_folder, f"{top_key}.json")

        # If value is None or empty, default to something (empty array or empty dict) if desired
        if value is None:
            value = []
        if isinstance(value, list) and len(value) == 0:
            # It's an empty list -> you can keep it as []
            pass
        if isinstance(value, dict) and not value:
            # It's an empty dict -> keep it as {}
            pass

        try:
            # We'll store it exactly as { top_key: value } so it matches
            # the structure of the old sub-JSON files.
            with open(out_path, "w") as f:
                json.dump({top_key: value}, f, indent=2)
            logger.info(f"[split_combined_json] Wrote: {out_path}")
        except Exception as e:
            logger.error(f"[split_combined_json] Error writing {out_path}: {e}")

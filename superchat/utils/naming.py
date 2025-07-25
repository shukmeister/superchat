# Utilities for generating safe names and identifiers

import re

# Convert any string to a valid Python identifier for agent names
def make_safe_identifier(name):
    # Replace any non-alphanumeric characters with underscores
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', name)
    # Ensure it doesn't start with a number
    if safe_name and safe_name[0].isdigit():
        safe_name = f"model_{safe_name}"
    # Remove consecutive underscores and trailing underscores
    safe_name = re.sub(r'_+', '_', safe_name).strip('_')
    # Ensure it's not empty
    if not safe_name:
        safe_name = "agent"
    return safe_name
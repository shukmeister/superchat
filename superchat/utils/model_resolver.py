"""Model resolution utility for handling user input to model selection.

This module provides a unified way to resolve user input (like "flash lite" or "deepseek") 
to actual model keys, with support for exact matching, fuzzy matching, and auto-selection.
"""

from typing import Dict, Tuple, Optional, List
from .fuzzy_matcher import find_matching_models, find_exact_match, should_auto_select


class ModelResolveResult:
    """Result of model resolution attempt."""
    
    def __init__(self, action_type: str, model_key: Optional[str] = None, 
                 message: Optional[str] = None, suggestions: Optional[List[str]] = None):
        self.action_type = action_type  # "selected", "suggest", "not_found"
        self.model_key = model_key
        self.message = message
        self.suggestions = suggestions or []


def resolve_model_from_input(user_input: str, models_config: Dict, 
                           context: str = "available") -> ModelResolveResult:
    """Resolve user input to a model key using exact and fuzzy matching.
    
    Args:
        user_input: The text the user typed (e.g., "flash lite", "deepseek")
        models_config: Models configuration dict (can be full config or subset)
        context: Context string for error messages ("available" or "current configuration")
        
    Returns:
        ModelResolveResult with action_type of:
        - "selected": model_key contains the resolved model, proceed with action
        - "suggest": suggestions contains list of model names to show user
        - "not_found": no matches found, show generic error
    """
    if not user_input.strip():
        return ModelResolveResult("not_found", message=f"No model name provided")
    
    # Try exact match first
    model_key = find_exact_match(user_input, models_config)
    
    if model_key:
        return ModelResolveResult("selected", model_key=model_key)
    
    # Try fuzzy matching
    matches = find_matching_models(user_input, models_config)
    
    if matches:
        # Check if we should auto-select the top match
        if should_auto_select(matches):
            return ModelResolveResult("selected", model_key=matches[0][0])
        else:
            # Show suggestions
            suggestions = [match[1] for match in matches[:3]]
            message = f"Multiple matches for '{user_input}'"
            if context != "available":
                message += f" in {context}"
            message += f":\nDid you mean: {', '.join(suggestions)}?"
            
            return ModelResolveResult("suggest", message=message, suggestions=suggestions)
    else:
        # No matches found
        message = f"Model '{user_input}' not found"
        if context != "available":
            message += f" in {context}"
        
        return ModelResolveResult("not_found", message=message)


def get_available_models_list(model_manager) -> str:
    """Generate comma-separated list of available model display names."""
    available_models = model_manager.get_available_models()
    display_names = []
    
    for model_key in available_models:
        model_config = model_manager.get_model_config(model_key)
        if model_config:
            family = model_config.get("family", "")
            model = model_config.get("model", "")
            release = model_config.get("release", "")
            parts = [family, model, release]
            display_name = " ".join(part for part in parts if part.strip()).strip()
            display_names.append(display_name)
        else:
            display_names.append(model_key)
    
    return ", ".join(display_names)


def get_display_name(model_data: Dict) -> str:
    """Generate human-readable display name for a model."""
    family = model_data.get("family", "")
    model = model_data.get("model", "")
    release = model_data.get("release", "")
    
    # Build base name from family and model
    base_parts = [family, model]
    base_name = " ".join(part for part in base_parts if part.strip()).strip()
    
    # Add release in parentheses if it exists
    if release and release.strip():
        return f"{base_name} ({release.strip()})"
    else:
        return base_name
"""Fuzzy matching utility for model selection.

This module provides fuzzy string matching capabilities to help users select models
using natural language input. Users can type any combination of words from a model's
company, family, model, and release fields and get relevant suggestions.
"""

from difflib import SequenceMatcher
from typing import List, Dict, Tuple


def find_matching_models(user_input: str, models_config: Dict) -> List[Tuple[str, str, float]]:
    """Find models that match user input using fuzzy string matching.
    
    Args:
        user_input: The text the user typed (e.g., "gemini pro", "deepseek", "k2")
        models_config: The models configuration dictionary from models.json
        
    Returns:
        List of tuples: (model_key, display_name, score)
        Sorted by score descending, only includes scores >= 0.4
    """
    if not user_input.strip():
        return []
    
    user_input = user_input.strip().lower()
    matches = []
    
    for model_key, model_data in models_config["models"].items():
        display_name = _get_display_name(model_data)
        score = _calculate_match_score(user_input, model_data, display_name)
        
        if score >= 0.4:
            matches.append((model_key, display_name, score))
    
    # Sort by score descending, then by display name for consistent ordering
    matches.sort(key=lambda x: (-x[2], x[1]))
    return matches


def should_auto_select(matches: List[Tuple[str, str, float]]) -> bool:
    """Determine if we should auto-select the top match based on confidence.
    
    Args:
        matches: List of (model_key, display_name, score) tuples, sorted by score
        
    Returns:
        True if we should auto-select the first match, False if we should show suggestions
    """
    if not matches:
        return False
    
    top_score = matches[0][2]
    
    # Don't auto-select if there are multiple perfect matches - let user choose
    if len(matches) >= 2 and matches[1][2] >= 0.95:
        return False
    
    # Auto-select if score is very high (0.8+) and clearly the best
    if top_score >= 0.8:
        return True
    
    # Auto-select if there's a clear winner (top score is significantly higher than second)
    if len(matches) >= 2:
        second_score = matches[1][2]
        score_gap = top_score - second_score
        # If top score is at least 0.6 and significantly better than second place
        if top_score >= 0.6 and score_gap >= 0.2:
            return True
    elif len(matches) == 1 and top_score >= 0.6:
        # Only one match and it's decent quality
        return True
    
    return False


def find_exact_match(user_input: str, models_config: Dict) -> str:
    """Find exact match for user input against model display names.
    
    Args:
        user_input: The text the user typed
        models_config: The models configuration dictionary from models.json
        
    Returns:
        Model key if exact match found, None otherwise
    """
    if not user_input.strip():
        return None
    
    user_input = user_input.strip().lower()
    
    for model_key, model_data in models_config["models"].items():
        display_name = _get_display_name(model_data).lower()
        if user_input == display_name:
            return model_key
    
    return None


def _get_display_name(model_data: Dict) -> str:
    """Generate human-readable display name for a model."""
    company = model_data.get("company", "")
    family = model_data.get("family", "")
    model = model_data.get("model", "")
    release = model_data.get("release", "")
    
    # Build display name: "Family Model Release" (skip company for brevity)
    parts = [family, model, release]
    return " ".join(part for part in parts if part.strip()).strip()


def _calculate_match_score(user_input: str, model_data: Dict, display_name: str) -> float:
    """Calculate fuzzy match score between user input and model data.
    
    Uses a weighted scoring system that rewards models matching more user words.
    """
    user_words = user_input.split()
    
    # Score against full display name first (highest weight)
    full_score = SequenceMatcher(None, user_input, display_name.lower()).ratio()
    
    # If we get a very high full match, use that
    if full_score >= 0.9:
        return full_score
    
    # Otherwise, use word-by-word matching with bonus for multiple matches
    all_words = []
    for field in ["company", "family", "model", "release"]:
        field_value = model_data.get(field, "")
        if field_value:
            # Split on spaces and periods to handle things like "2.5"
            words = field_value.replace(".", " ").split()
            all_words.extend([w.lower() for w in words if w.strip()])
    
    if len(user_words) == 1:
        # Single word input - find best matching word
        best_word_score = 0.0
        for model_word in all_words:
            word_score = SequenceMatcher(None, user_input, model_word).ratio()
            best_word_score = max(best_word_score, word_score)
        return max(full_score, best_word_score)
    
    # Multiple words - reward models that match more user words
    matched_user_words = 0
    total_word_score = 0.0
    
    for user_word in user_words:
        best_match_for_word = 0.0
        for model_word in all_words:
            word_score = SequenceMatcher(None, user_word, model_word).ratio()
            best_match_for_word = max(best_match_for_word, word_score)
        
        # Consider a word "matched" if it has a good similarity
        if best_match_for_word >= 0.7:
            matched_user_words += 1
        
        total_word_score += best_match_for_word
    
    # Calculate score based on percentage of user words matched and average quality
    if len(user_words) > 0:
        word_coverage = matched_user_words / len(user_words)
        avg_word_score = total_word_score / len(user_words)
        combined_score = (word_coverage * 0.7) + (avg_word_score * 0.3)
        return max(full_score, combined_score)
    
    return full_score
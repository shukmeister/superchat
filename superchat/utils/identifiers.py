"""Model identifier utilities for Russian letter assignments."""

def get_model_identifier(model_index):
    """Get Russian letter identifier for a model by its index position.
    
    Args:
        model_index (int): Zero-based index of the model (0, 1, 2, etc.)
        
    Returns:
        str: Russian letter or numeric identifier (e.g., 'д', 'ф', 'ш', '#4')
    """
    russian_letters = ['д', 'ф', 'ш', 'в', 'г', 'л']
    return russian_letters[model_index] if model_index < len(russian_letters) else f"#{model_index+1}"
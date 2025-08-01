# Session statistics and usage tracking utilities

# Calculate cost for a single model based on token usage
def calculate_model_cost(model_config, input_tokens, output_tokens):
    input_cost_per_million = model_config.get("input_cost", 0)
    output_cost_per_million = model_config.get("output_cost", 0)
    
    input_cost = (input_tokens / 1_000_000) * input_cost_per_million
    output_cost = (output_tokens / 1_000_000) * output_cost_per_million
    return input_cost + output_cost


# Calculate total cost and per-model breakdown for all models
def calculate_total_cost(stats, models, model_client_manager, return_breakdown=False):
    total_cost = 0
    model_breakdown = []
    
    for model_name in models:
        model_config = model_client_manager.get_model_config(model_name)
        if model_config:
            # Distribute tokens evenly across models (simplified approach)
            # TODO: Track per-agent usage for more accurate cost calculation
            input_tokens = stats['total_input_tokens'] / len(models)
            output_tokens = stats['total_output_tokens'] / len(models)
            
            model_cost = calculate_model_cost(model_config, input_tokens, output_tokens)
            total_cost += model_cost
            
            if return_breakdown:
                model = model_config.get("model", model_name)
                model_breakdown.append((model, model_cost))
    
    if return_breakdown:
        return total_cost, model_breakdown
    return total_cost


# Extract token usage data from AutoGen TaskResult for statistics
def extract_usage_from_task_result(task_result):
    total_prompt_tokens = 0
    total_completion_tokens = 0
    
    # Iterate through all messages and accumulate token counts
    for message in task_result.messages:
        # Check if message has usage data attached
        if hasattr(message, 'models_usage') and message.models_usage:
            # Handle both single RequestUsage object and list of RequestUsage objects
            usage_items = message.models_usage if isinstance(message.models_usage, list) else [message.models_usage]
            
            for usage in usage_items:
                if hasattr(usage, 'prompt_tokens'):
                    total_prompt_tokens += usage.prompt_tokens
                if hasattr(usage, 'completion_tokens'):
                    total_completion_tokens += usage.completion_tokens
    
    if total_prompt_tokens > 0 or total_completion_tokens > 0:
        return {
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "total_tokens": total_prompt_tokens + total_completion_tokens
        }
    return None

# Display detailed session statistics including token counts and costs
def display_stats(stats, models, model_client_manager):
    print("Session Statistics:")
    print(f"  Time elapsed: {stats['duration']}")
    print(f"  Conversation rounds: {stats['conversation_rounds']}")
    print()
    print("Token Usage:")
    print(f"  Input tokens:  {stats['total_input_tokens']:,}")
    print(f"  Output tokens: {stats['total_output_tokens']:,}")
    print(f"  Total tokens:  {stats['total_tokens']:,}")
    
    # Calculate and display costs with per-model breakdown
    print()
    print("Estimated Costs:")
    
    total_cost, model_breakdown = calculate_total_cost(stats, models, model_client_manager, return_breakdown=True)
    
    for model, model_cost in model_breakdown:
        print(f"  {model}: ${model_cost:.6f}")
    
    print(f"  Total cost: ${total_cost:.6f}")


# Display brief session summary when user exits
def display_exit_summary(stats, models, model_client_manager):
    print("Session Summary:")
    print(f"  Time elapsed: {stats['duration']}")
    print(f"  Conversation rounds: {stats['conversation_rounds']}")
    print(f"  Total tokens: {stats['total_tokens']:,}")
    
    # Calculate and display total cost only
    total_cost = calculate_total_cost(stats, models, model_client_manager)
    
    if total_cost > 0:
        print(f"  Total cost: ${total_cost:.6f}")
    print()
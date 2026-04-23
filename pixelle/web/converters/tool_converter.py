def tools_from_chaintlit_to_openai(chainlit_tools: list[dict]) -> dict:
    openai_tools = []
    for t in chainlit_tools:
        input_schema = (getattr(t, 'inputSchema', {}) if not isinstance(t, dict) else t.get('inputSchema')) or {}
        properties = input_schema.get("properties") or {}
        
        # Stelle sicher, dass jedes Property ein valides Dict mit Typ ist
        for prop_name, prop_values in properties.items():
            if not isinstance(prop_values, dict):
                properties[prop_name] = {"type": "string"} # Fallback
                continue
            if "type" not in prop_values or prop_values["type"] is None:
                prop_values["type"] = "string"

        name = getattr(t, 'name', '') if not isinstance(t, dict) else t.get('name', '')
        description = getattr(t, 'description', '') if not isinstance(t, dict) else t.get('description', '')

        openai_tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": input_schema.get("required") or [],
                    "additionalProperties": False # Sehr wichtig für neue OpenWebUI/OpenAI Versionen!
                }
            }
        })
    return openai_tools

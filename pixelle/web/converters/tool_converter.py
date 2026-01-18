def tools_from_chaintlit_to_openai(chainlit_tools: list[dict]) -> dict:
    openai_tools = []
    for t in chainlit_tools:
        # Sicherer Zugriff auf das Schema
        input_schema = getattr(t, 'inputSchema', {}) if not isinstance(t, dict) else t.get('inputSchema', {})
        properties = input_schema.get("properties", {})
        
        # Jedes Property prüfen: Wenn 'type' fehlt oder null ist -> auf 'string' setzen
        for prop_name, prop_values in properties.items():
            if "type" not in prop_values or prop_values["type"] is None:
                prop_values["type"] = "string"

        openai_tools.append({
            "type": "function",
            "function": {
                "name": getattr(t, 'name', '') if not isinstance(t, dict) else t.get('name', ''),
                "description": getattr(t, 'description', '') if not isinstance(t, dict) else t.get('description', ''),
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": input_schema.get("required", [])
                }
            }
        })
    return openai_tools

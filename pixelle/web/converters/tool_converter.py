def tools_from_chaintlit_to_openai(chainlit_tools: list[dict]) -> dict:
    openai_tools = []
    for t in chainlit_tools:
        # Input Schema abrufen (Default zu leerem Dict)
        input_schema = (getattr(t, 'inputSchema', {}) if not isinstance(t, dict) else t.get('inputSchema')) or {}
        
        # Properties abrufen
        properties = input_schema.get("properties") or {}
        
        # Jedes Property prüfen: Wenn 'type' fehlt oder null ist -> auf 'string' setzen
        for prop_name, prop_values in properties.items():
            if not isinstance(prop_values, dict):
                continue
            if "type" not in prop_values or prop_values["type"] is None:
                prop_values["type"] = "string"

        # Name und Beschreibung sicher abrufen (None -> "")
        raw_name = getattr(t, 'name', '') if not isinstance(t, dict) else t.get('name')
        name = raw_name if raw_name is not None else ""

        raw_desc = getattr(t, 'description', '') if not isinstance(t, dict) else t.get('description')
        description = raw_desc if raw_desc is not None else ""

        # Required fields sicherstellen
        required = input_schema.get("required")
        if required is None:
            required = []

        openai_tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        })
    return openai_tools

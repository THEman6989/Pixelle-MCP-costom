import aiohttp
from pixelle.mcp_core import mcp
from pixelle.settings import settings

@mcp.tool()
async def stop_all_generations() -> str:
    """Stoppt sofort alle laufenden Generierungen auf dem ComfyUI Server."""
    base_url = settings.comfyui_base_url.rstrip('/')
    interrupt_url = f"{base_url}/interrupt"
    
    try:
        async with aiohttp.ClientSession() as session:
            # 1. Laufende Generierung unterbrechen
            async with session.post(interrupt_url) as response:
                if response.status == 200:
                    # 2. Optional: Warteschlange löschen (Queue clear)
                    async with session.post(f"{base_url}/queue", json={"clear": True}) as q_resp:
                        return "✅ Notbremse gezogen! ComfyUI wurde unterbrochen und die Queue bereinigt."
                else:
                    return f"❌ Fehler beim Stoppen: HTTP {response.status}"
    except Exception as e:
        return f"❌ Verbindungsfehler: {str(e)}"

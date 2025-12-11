import asyncio
import aiohttp
from pixelle.mcp_core import mcp
from pixelle.settings import settings

# --- 🔧 KONFIGURATION (BITTE AN DEINEN SERVER ANPASSEN!) ---
SSH_USER = "root"               # Dein Benutzername auf dem ComfyUI-Server
SSH_HOST = "192.168.1.XX"       # Die IP deines Servers (muss erreichbar sein)
PM2_APP_NAME = "ComfyUI"        # Der exakte Name aus 'pm2 list' auf dem Server

# -----------------------------------------------------------

@mcp.tool()
async def restart_comfyui_server() -> str:
    """
    💀 TERMINATOR: Startet den ComfyUI Server via SSH/PM2 komplett neu.
    Nutze dies NUR, wenn der Server hängt oder nicht mehr reagiert.
    Dies entspricht dem Ziehen des Steckers (Hard Reset).
    """
    # Wir nutzen den nativen SSH-Client deines Laptops.
    # BatchMode=yes verhindert, dass das Skript hängen bleibt, falls ein Passwort gefragt wird.
    ssh_cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        f"{SSH_USER}@{SSH_HOST}",
        f"pm2 restart {PM2_APP_NAME}"
    ]
    
    try:
        # Prozess starten
        proc = await asyncio.create_subprocess_exec(
            *ssh_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode == 0:
            return f"✅ **Terminator erfolgreich:** Prozess '{PM2_APP_NAME}' wurde neu gestartet."
        else:
            error_msg = stderr.decode().strip()
            return f"❌ **Fehler beim Neustart:**\nSSH meldet: {error_msg}\n(Stimmen User, IP und PM2-Name?)"
    except Exception as e:
        return f"❌ Kritischer Fehler beim Ausführen: {str(e)}"


@mcp.tool()
async def interrupt_current_generation() -> str:
    """
    🛑 NOTBREMSE: Stoppt die aktuelle Generierung sanft über die API.
    Der Server bleibt an, nur das aktuelle Bild wird abgebrochen.
    Nutze dies, wenn du dich umentschieden hast.
    """
    # URL aus den Settings laden (die aus deiner .env Datei)
    base_url = (settings.comfyui_base_url or "http://127.0.0.1:8188").rstrip('/')
    
    try:
        async with aiohttp.ClientSession() as session:
            # 1. Interrupt senden (Stoppt die Rechnung)
            async with session.post(f"{base_url}/interrupt") as response:
                if response.status == 200:
                    # 2. Queue leeren (Damit nicht das nächste Bild direkt startet)
                    await session.post(f"{base_url}/queue", json={"clear": True})
                    return "🛑 **Abgebrochen:** Generierung gestoppt und Warteschlange geleert."
                else:
                    return f"⚠️ API-Fehler ({response.status}). Der Server reagiert komisch. Wenn er hängt, nutze 'restart_comfyui_server'."
    except Exception as e:
        return f"❌ Verbindung fehlgeschlagen. Der Server scheint tot zu sein. Nutze 'restart_comfyui_server'."


@mcp.tool()
async def get_server_logs(lines: int = 50) -> str:
    """
    📋 DIAGNOSE: Holt die letzten Zeilen der Server-Logs via SSH.
    """
    log_cmd = f"tail -n {lines} ~/.pm2/logs/{PM2_APP_NAME}-out.log ~/.pm2/logs/{PM2_APP_NAME}-error.log"
    
    ssh_cmd = [
        "ssh", "-o", "BatchMode=yes",
        f"{SSH_USER}@{SSH_HOST}", log_cmd
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *ssh_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            logs = stdout.decode().strip()
            # Hier ist der Trick für Open WebUI: HTML Details Tags!
            # Wir "escapen" spitze Klammern, damit kein falsches HTML entsteht.
            safe_logs = logs.replace("<", "&lt;").replace(">", "&gt;")
            
            return f"""
<details>
<summary>📋 <b>Klicke hier, um die Server-Logs zu sehen ({lines} Zeilen)</b></summary>
<br>
<pre><code>
{safe_logs}
</code></pre>
</details>
"""
        else:
            return f"❌ Fehler beim Log-Abruf: {stderr.decode().strip()}"

    except Exception as e:
        return f"❌ Kritischer Fehler: {str(e)}"

import asyncio
import aiohttp
import shutil
from pixelle.mcp_core import mcp
from pixelle.settings import settings

# --- 🔧 KONFIGURATION (BITTE ANPASSEN!) ---
SSH_USER = "amin"               # Ihr Ubuntu-Benutzername
SSH_PASS = "IhrPasswortHier"    # <--- HIER DAS PASSWORT EINTRAGEN
SSH_HOST = "192.168.178.49"     # Die IP Ihres Servers (aus dem Chatverlauf)
PM2_APP_NAME = "ComfyUI"        # Name des Prozesses in PM2 (meist 'ComfyUI')
# -----------------------------------------------------------

def build_ssh_command(remote_command: str) -> list:
    """
    Erstellt den SSH-Befehl. Wenn ein Passwort gesetzt ist,
    wird 'sshpass' verwendet, um das Passwort automatisch einzugeben.
    """
    # Basis-SSH-Befehl (ohne Passwort-Prompt, akzeptiert Host-Key automatisch)
    base_ssh = [
        "ssh",
        "-o", "BatchMode=no",                   # BatchMode muss bei sshpass 'no' sein
        "-o", "StrictHostKeyChecking=no",       # Verhindert "Are you sure..." Frage
        "-o", "UserKnownHostsFile=/dev/null",   # Speichert keine Keys (vermeidet Müll)
        f"{SSH_USER}@{SSH_HOST}",
        remote_command
    ]

    # Wenn ein Passwort konfiguriert ist und sshpass installiert ist:
    if SSH_PASS and shutil.which("sshpass"):
        return ["sshpass", "-p", SSH_PASS] + base_ssh
    else:
        # Fallback: Versucht Key-Based Auth, wenn kein Passwort oder sshpass fehlt
        return base_ssh


@mcp.tool()
async def restart_comfyui_server() -> str:
    """
    💀 TERMINATOR: Startet den ComfyUI Server via SSH/PM2 komplett neu.
    Nutzt das konfigurierte Passwort für den SSH-Zugriff.
    """
    # Befehl für den Server
    remote_cmd = f"pm2 restart {PM2_APP_NAME}"
    
    # Befehl zusammenbauen (mit sshpass wenn nötig)
    full_cmd = build_ssh_command(remote_cmd)
    
    try:
        # Prozess starten
        proc = await asyncio.create_subprocess_exec(
            *full_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode == 0:
            return f"✅ **Terminator erfolgreich:** Prozess '{PM2_APP_NAME}' auf {SSH_HOST} neu gestartet."
        else:
            error_msg = stderr.decode().strip()
            return (f"❌ **Fehler beim Neustart:**\nSSH meldet: {error_msg}\n"
                    f"Tipp: Ist 'sshpass' installiert? (sudo apt install sshpass)")
    except Exception as e:
        return f"❌ Kritischer Fehler beim Ausführen: {str(e)}"


@mcp.tool()
async def interrupt_current_generation() -> str:
    """
    🛑 NOTBREMSE: Stoppt die aktuelle Generierung sanft über die API.
    (Benötigt kein SSH-Passwort, da es über HTTP läuft)
    """
    base_url = (settings.comfyui_base_url or f"http://{SSH_HOST}:8188").rstrip('/')
    
    try:
        async with aiohttp.ClientSession() as session:
            # 1. Interrupt senden
            async with session.post(f"{base_url}/interrupt") as response:
                if response.status == 200:
                    # 2. Queue leeren
                    await session.post(f"{base_url}/queue", json={"clear": True})
                    return "🛑 **Abgebrochen:** Generierung gestoppt und Warteschlange geleert."
                else:
                    return f"⚠️ API-Fehler ({response.status}). Der Server reagiert komisch."
    except Exception as e:
        return f"❌ Verbindung zur API fehlgeschlagen ({base_url}). Nutze 'restart_comfyui_server'."


@mcp.tool()
async def get_server_logs(lines: int = 50) -> str:
    """
    📋 DIAGNOSE: Holt die letzten Zeilen der Server-Logs via SSH mit Passwort.
    """
    # Log-Befehl für PM2
    remote_cmd = f"tail -n {lines} ~/.pm2/logs/{PM2_APP_NAME}-out.log ~/.pm2/logs/{PM2_APP_NAME}-error.log"
    
    full_cmd = build_ssh_command(remote_cmd)

    try:
        proc = await asyncio.create_subprocess_exec(
            *full_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            logs = stdout.decode().strip()
            # HTML-Safe machen für WebUI
            safe_logs = logs.replace("<", "&lt;").replace(">", "&gt;")
            
            return f"""
<details>
<summary>📋 <b>Server-Logs von {SSH_HOST} ({lines} Zeilen)</b></summary>
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

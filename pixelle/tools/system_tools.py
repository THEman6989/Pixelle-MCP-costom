import asyncio
import aiohttp
import shutil
from pixelle.mcp_core import mcp
from pixelle.settings import settings  # Wir laden alles aus settings.py

# --- 🔧 KONFIGURATION ---
# Die Daten werden jetzt sicher aus der .env Datei oder settings.py geladen
PM2_APP_NAME = "ComfyUI"
# ------------------------

def build_ssh_command(remote_command: str) -> list:
    """
    Erstellt den SSH-Befehl dynamisch basierend auf den Einstellungen.
    """
    # Daten aus Settings holen
    host = settings.ssh_host
    user = settings.ssh_user
    password = settings.ssh_password

    # Basis-SSH-Befehl
    base_ssh = [
        "ssh",
        "-o", "BatchMode=no",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        f"{user}@{host}",
        remote_command
    ]

    # Wenn ein Passwort in der .env steht und sshpass installiert ist:
    if password and shutil.which("sshpass"):
        return ["sshpass", "-p", password] + base_ssh
    else:
        # Fallback: Versucht Key-Based Auth
        return base_ssh


@mcp.tool()
async def restart_comfyui_server() -> str:
    """
    💀 TERMINATOR: Startet den ComfyUI Server via SSH/PM2 komplett neu.
    Holt Host, User und Passwort sicher aus der Konfiguration.
    """
    remote_cmd = f"pm2 restart {PM2_APP_NAME}"
    full_cmd = build_ssh_command(remote_cmd)
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *full_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode == 0:
            return f"✅ **Terminator erfolgreich:** Prozess '{PM2_APP_NAME}' auf {settings.ssh_host} neu gestartet."
        else:
            error_msg = stderr.decode().strip()
            return (f"❌ **Fehler beim Neustart:**\nSSH meldet: {error_msg}\n"
                    f"Hinweis: Prüfen Sie SSH_PASSWORD in der .env Datei.")
    except Exception as e:
        return f"❌ Kritischer Fehler beim Ausführen: {str(e)}"


@mcp.tool()
async def interrupt_current_generation() -> str:
    """
    🛑 NOTBREMSE: Stoppt die aktuelle Generierung sanft über die API.
    """
    # Nutzt den Host aus den Settings oder Fallback auf localhost
    host = settings.ssh_host if settings.ssh_host else "127.0.0.1"
    base_url = (settings.comfyui_base_url or f"http://{host}:8188").rstrip('/')
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{base_url}/interrupt") as response:
                if response.status == 200:
                    await session.post(f"{base_url}/queue", json={"clear": True})
                    return "🛑 **Abgebrochen:** Generierung gestoppt und Warteschlange geleert."
                else:
                    return f"⚠️ API-Fehler ({response.status}). Der Server reagiert komisch."
    except Exception as e:
        return f"❌ Verbindung zur API fehlgeschlagen ({base_url}). Nutze 'restart_comfyui_server'."


@mcp.tool()
async def get_server_logs(lines: int = 50) -> str:
    """
    📋 DIAGNOSE: Holt die letzten Zeilen der Server-Logs via SSH.
    """
    remote_cmd = f"tail -n {lines} ~/.pm2/logs/{PM2_APP_NAME}-out.log ~/.pm2/logs/{PM2_APP_NAME}-error.log"
    full_cmd = build_ssh_command(remote_cmd)

    try:
        proc = await asyncio.create_subprocess_exec(
            *full_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            logs = stdout.decode().strip()
            safe_logs = logs.replace("<", "&lt;").replace(">", "&gt;")
            return f"""
<details>
<summary>📋 <b>Server-Logs von {settings.ssh_host} ({lines} Zeilen)</b></summary>
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

    except Exception as e:
        return f"❌ Kritischer Fehler: {str(e)}"

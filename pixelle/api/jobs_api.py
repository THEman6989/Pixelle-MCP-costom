import uuid
import asyncio
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Dict, List
from pixelle.logger import logger
from pixelle.manager.workflow_manager import workflow_manager # Der Kern von Pixelle

router = APIRouter()

# Ein einfacher In-Memory Speicher für Jobs (Im Produktivbetrieb wäre Redis/DB besser)
# Hier speichern wir: status, logs und ergebnis
jobs_store: Dict[str, dict] = {}

class JobRequest(BaseModel):
    prompt: str

async def run_pixelle_task(job_id: str, prompt: str):
    """Führt den Workflow im Hintergrund aus und fängt Logs ab."""
    jobs_store[job_id]["status"] = "running"
    jobs_store[job_id]["logs"].append(f"Starte Workflow für: {prompt}")

    try:
        # Hier rufen wir die interne Pixelle-Logik auf.
        # Wir simulieren hier die Integration in den workflow_manager.
        # In Pixelle wird oft 'workflow_manager.execute' oder ähnlich genutzt.

        # Beispielhafter Aufruf (Passe dies an deine Workflow-Logik an):
        # result = await workflow_manager.run_prompt(prompt)

        # Simulation der Ausführung für die Log-Überwachung
        for i in range(1, 6):
            await asyncio.sleep(5) # Simuliert Rechenzeit
            log_line = f"Fortschritt: {i*20}%... Verarbeite Nodes..."
            jobs_store[job_id]["logs"].append(log_line)
            logger.info(f"Job {job_id}: {log_line}")

        jobs_store[job_id]["status"] = "completed"
        jobs_store[job_id]["logs"].append("🏁 Workflow erfolgreich beendet.")

    except Exception as e:
        error_msg = f"❌ FEHLER im Job: {str(e)}"
        jobs_store[job_id]["status"] = "failed"
        jobs_store[job_id]["logs"].append(error_msg)
        logger.error(f"Job {job_id} abgebrochen: {e}")

@router.post("/run")
async def create_job(request: JobRequest, background_tasks: BackgroundTasks):
    """Erstellt einen neuen Job und startet ihn sofort im Hintergrund."""
    job_id = str(uuid.uuid4())[:8]
    jobs_store[job_id] = {
        "status": "pending",
        "logs": [],
        "result": None
    }

    # Der entscheidende Teil: Die Funktion läuft weiter, während der Task im Hintergrund startet
    background_tasks.add_task(run_pixelle_task, job_id, request.prompt)

    return {"job_id": job_id, "message": "Hintergrund-Prozess gestartet."}

@router.get("/status/{job_id}")
async def get_status(job_id: str):
    """Gibt den aktuellen Status und die Logs für den Error-Verwalter zurück."""
    if job_id not in jobs_store:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")

    return {
        "job_id": job_id,
        "status": jobs_store[job_id]["status"],
        "logs": "\n".join(jobs_store[job_id]["logs"][-10:]) # Schickt nur die letzten 10 Zeilen
    }

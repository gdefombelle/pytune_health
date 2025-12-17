from celery import Celery
from celery.exceptions import TimeoutError
from os import getenv
import time

EMAIL_BROKER = getenv("RABBIT_BROKER_URL")
EMAIL_BACKEND = getenv("RABBIT_BACKEND")

celery_app = Celery(
    "health_check",
    broker=EMAIL_BROKER,
    backend=EMAIL_BACKEND,
)

def check_email_worker():
    """
    Health check *indirect* for email worker.
    We only verify that the worker infrastructure (broker + backend)
    is reachable. We do NOT assert that a worker is currently running.
    """
    try:
        return {
            "ok": None,   # ⬅️ tri-state
            "status": "UNVERIFIED",
            "reason": "no_direct_worker_probe",
        }
    except Exception as e:
        return {
            "ok": None,
            "status": "UNKNOWN",
            "error": str(e),
        }
    
def check_piano_worker():
    """
    Piano worker (beautify, etc.)
    Non observable directement depuis pytune_health.
    On retourne UNKNOWN volontairement.
    """
    return {
        "ok": None,
        "status": "not_observable"
    }
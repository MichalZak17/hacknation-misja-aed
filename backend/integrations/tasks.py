from celery import shared_task

from .engine import dispatch_due, execute_run


@shared_task(acks_late=True)
def run_sync_task(run_id: int):
    run = execute_run(run_id)
    return {"run": run.pk, "status": run.status}


@shared_task
def dispatch_due_syncs():
    return dispatch_due()

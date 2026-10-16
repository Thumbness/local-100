import secrets
import threading
import time
from typing import Callable


class JobContext:
    """Passed to a job's work function so it can report progress and wait for the user."""

    def __init__(self, store: "JobStore", job_id: str):
        self._store = store
        self._job_id = job_id

    def progress(self, message: str, done: int | None = None, total: int | None = None,
                 details: dict | None = None):
        fields = {"message": message, "done": done, "total": total}
        if details is not None:  # details persist until replaced
            fields["details"] = details
        self._store.update(self._job_id, **fields)

    def wait_for_user(self, prompt: dict):
        """Show `prompt` to the user and block until they call JobStore.resume()."""
        gate = threading.Event()
        self._store.update(self._job_id, prompt=prompt, gate=gate)
        gate.wait()
        self._store.update(self._job_id, prompt=None, gate=None)


class JobStore:
    """In-memory background jobs. Requires a single server process."""

    def __init__(self, ttl_seconds: int = 3600):
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds

    def start(self, work: Callable[[JobContext], dict], **meta) -> str:
        """Run `work` in a background thread. Extra keyword arguments are kept on the job (e.g. year=2016)."""
        job_id = secrets.token_urlsafe(12)
        now = time.time()
        with self._lock:
            # Drop finished jobs past their TTL so memory doesn't grow forever
            expired = [k for k, v in self._jobs.items()
                       if v["status"] != "running" and now - v["created"] > self._ttl]
            for old_id in expired:
                del self._jobs[old_id]
            self._jobs[job_id] = {
                "status": "running", "message": "Starting", "done": None, "total": None,
                "error": None, "result": None, "prompt": None, "gate": None, "details": None,
                "created": now,
                **meta,
            }
        threading.Thread(target=self._run, args=(job_id, work), daemon=True).start()
        return job_id

    def _run(self, job_id: str, work: Callable[[JobContext], dict]):
        try:
            result = work(JobContext(self, job_id))
            self.update(job_id, status="done", message="Done", result=result)
        except Exception as e:
            self.update(job_id, status="error", message="Something went wrong", error=str(e))

    def update(self, job_id: str, **fields):
        with self._lock:
            self._jobs[job_id].update(fields)

    def snapshot(self, job_id: str) -> dict | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def running_job_id(self) -> str | None:
        with self._lock:
            for job_id, job in self._jobs.items():
                if job["status"] == "running":
                    return job_id
        return None

    def resume(self, job_id: str) -> bool:
        """Release a job that is waiting in wait_for_user(). Returns False if nothing is waiting."""
        job = self.snapshot(job_id)
        if not job or job["gate"] is None:
            return False
        job["gate"].set()
        return True

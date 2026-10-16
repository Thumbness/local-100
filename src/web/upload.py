import json

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

from ..application.jobs import JobContext, JobStore
from ..composition import countdown_service

upload_bp = Blueprint("upload", __name__, url_prefix="/upload")
jobs = JobStore()


def import_job(raw, ctx: JobContext) -> dict:
    """Runs in the background. A YouTube sign-in prompt is shown to the user on the progress page."""
    service = countdown_service(
        oauth_verifier=lambda url, code: ctx.wait_for_user({"url": url, "code": code}),
    )
    return service.import_raw(raw, ctx.progress)


@upload_bp.route("/", methods=["GET", "POST"])
def upload_page():
    if request.method == "GET":
        return render_template("upload_form.html", error=None)

    if jobs.running_job_id():
        return render_template(
            "upload_form.html",
            error="A download is already running. Wait for it to finish.",
        ), 409

    file = request.files.get("file")
    if not file or not file.filename.lower().endswith(".json"):
        return render_template("upload_form.html", error="Choose a .json file."), 400

    try:
        raw = json.load(file.stream)
    except ValueError:
        return render_template("upload_form.html", error="That file isn't valid JSON."), 400

    problem = countdown_service().check_raw(raw)
    if problem:
        return render_template("upload_form.html", error=problem), 400

    job_id = jobs.start(lambda ctx: import_job(raw, ctx))
    return redirect(url_for("upload.job_page", job_id=job_id))


@upload_bp.route("/jobs/<job_id>")
def job_page(job_id):
    if jobs.snapshot(job_id) is None:
        return redirect(url_for("upload.upload_page"))
    return render_template(
        "job_progress.html",
        title="Downloading countdown videos",
        subtitle="This can take a long time for a full countdown. You can leave this page open.",
        poll_url=url_for("upload.job_status", job_id=job_id),
        continue_url=url_for("upload.resume_job", job_id=job_id),
        back_url=url_for("upload.upload_page"),
        back_label="Upload a different file",
    )


@upload_bp.route("/api/jobs/<job_id>/continue", methods=["POST"])
def resume_job(job_id):
    """The user says they've finished the YouTube sign-in; release the waiting download."""
    if not jobs.resume(job_id):
        return jsonify(error="Nothing is waiting for sign-in"), 409
    return jsonify(ok=True)


@upload_bp.route("/api/jobs/<job_id>")
def job_status(job_id):
    job = jobs.snapshot(job_id)
    if job is None:
        return jsonify(error="Job not found"), 404

    body = {k: job[k] for k in ("status", "message", "done", "total", "error", "prompt", "details")}
    if job["status"] == "done":
        report = job["result"]
        key = "notice" if report["ok"] else "error"
        body["redirect"] = url_for("home", **{key: report["message"]})
    return jsonify(body)

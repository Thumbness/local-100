import secrets
from dataclasses import asdict
from datetime import date

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
from spotipy.cache_handler import FlaskSessionCacheHandler

from ..application.jobs import JobStore
from ..application.albums.find_albums import find_album_releases
from ..infrastructure.spotify.auth import build_oauth, client_from_token

library_bp = Blueprint("library", __name__, url_prefix="/library")

MIN_YEAR = 1900
MAX_JOBS_PER_SESSION = 10
jobs = JobStore()


def make_auth():
    """OAuth helper that keeps the logged-in user's tokens in their Flask session."""
    return build_oauth(FlaskSessionCacheHandler(session))


def valid_year(raw):
    try:
        year = int(raw)
    except (TypeError, ValueError):
        return None
    return year if MIN_YEAR <= year <= date.today().year else None


def get_owned_job(job_id):
    """The job, but only if this browser session started it."""
    if job_id not in session.get("jobs", []):
        return None
    return jobs.snapshot(job_id)


def job_view(job):
    return {k: job[k] for k in ("status", "message", "done", "total", "error", "prompt", "details")}


@library_bp.route("/login")
def login():
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state
    return redirect(make_auth().get_authorize_url(state=state))


@library_bp.route("/callback")
def callback():
    if request.args.get("error"):
        return redirect(url_for("home", error="Spotify login was cancelled."))

    expected_state = session.pop("oauth_state", None)
    if not expected_state or request.args.get("state") != expected_state:
        return redirect(url_for("home", error="Login check failed. Please try again."))

    code = request.args.get("code")
    if not code:
        return redirect(url_for("home", error="Spotify did not return an authorization code."))

    make_auth().get_access_token(code)  # stores tokens in the session
    return redirect(url_for("library.search"))


@library_bp.route("/", methods=["GET", "POST"])
def search():
    token_info = make_auth().cache_handler.get_cached_token()
    if not token_info:
        return redirect(url_for("library.login"))

    this_year = date.today().year
    if request.method == "GET":
        return render_template("library_search.html", error=None, this_year=this_year, min_year=MIN_YEAR)

    year = valid_year(request.form.get("year", "").strip())
    if year is None:
        return render_template(
            "library_search.html",
            error=f"Enter a year between {MIN_YEAR} and {this_year}.",
            this_year=this_year,
            min_year=MIN_YEAR,
        ), 400

    def work(ctx):
        spotify = client_from_token(dict(token_info))
        releases = find_album_releases(spotify, year, ctx.progress)
        return {"year": year, "albums": [asdict(r) for r in releases]}

    job_id = jobs.start(work, year=year)
    session["jobs"] = (session.get("jobs", []) + [job_id])[-MAX_JOBS_PER_SESSION:]
    return redirect(url_for("library.job_page", job_id=job_id))


@library_bp.route("/jobs/<job_id>")
def job_page(job_id):
    job = get_owned_job(job_id)
    if job is None:
        return redirect(url_for("library.search"))
    if job["status"] == "done":
        return redirect(url_for("library.job_results", job_id=job_id))
    return render_template(
        "job_progress.html",
        title=f"Searching {job['year']}",
        subtitle="This can take a few minutes for large libraries. You can leave this page open.",
        poll_url=url_for("library.job_status", job_id=job_id),
        back_url=url_for("library.search"),
        back_label="Start a new search",
    )


@library_bp.route("/api/jobs/<job_id>")
def job_status(job_id):
    job = get_owned_job(job_id)
    if job is None:
        return jsonify(error="Job not found"), 404

    body = job_view(job)
    if job["status"] == "done":
        body["redirect"] = url_for("library.job_results", job_id=job_id)
    return jsonify(body)


@library_bp.route("/results/<job_id>")
def job_results(job_id):
    job = get_owned_job(job_id)
    if job is None:
        return redirect(url_for("library.search"))
    if job["status"] != "done":
        return redirect(url_for("library.job_page", job_id=job_id))
    return render_template("library_results.html", year=job["result"]["year"], albums=job["result"]["albums"])


@library_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

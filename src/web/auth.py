from urllib.parse import urlsplit

from flask import Blueprint, abort, g, jsonify, redirect, render_template, request, session, url_for

from ..composition import auth_service
from ..domain.auth.user import InvalidCredentials, TooManyAttempts

auth_bp = Blueprint("auth", __name__)

# Reachable without signing in: the login page, the load balancer health check, and CSS/images
PUBLIC_ENDPOINTS = {"auth.login", "healthz", "static"}


def current_user():
    """The signed-in user for this request. Checked against the user list every time, so removing a user
    or revoking admin takes effect on their next request."""
    if "user" not in g:
        g.user = None
        name = session.get("user")
        if name:
            g.user = auth_service().user_for(name)
            if g.user is None:
                session.pop("user", None)
    return g.user


def safe_next(target: str | None) -> str | None:
    """Only follow a 'next' address that stays inside this app (no open redirect)."""
    if not target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or not target.startswith("/") or target.startswith("//") or "\\" in target:
        return None
    return target


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    service = auth_service()
    if current_user():
        return redirect(url_for("home"))

    next_url = safe_next(request.values.get("next"))
    error, status = None, 200
    if request.method == "POST":
        try:
            user = service.login(
                request.form.get("username", ""),
                request.form.get("password", ""),
                request.remote_addr or "unknown",
            )
        except TooManyAttempts as e:
            minutes = max(1, -(-e.retry_after_seconds // 60))
            error, status = f"Too many attempts. Try again in {minutes} minute(s).", 429
        except InvalidCredentials:
            error, status = "Wrong username or password.", 401
        else:
            session.clear()  # a fresh session on every sign-in
            session["user"] = user.username
            session.permanent = True
            return redirect(next_url or url_for("home"))

    return render_template("login.html", error=error, next_url=next_url, has_users=service.has_users()), status


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


def install_auth(app):
    """Put the whole app behind the login. /upload is for admins only."""
    app.register_blueprint(auth_bp)

    @app.before_request
    def require_login():
        endpoint = request.endpoint
        if endpoint is None or endpoint in PUBLIC_ENDPOINTS:  # None: unknown URL, let Flask answer 404
            return None

        user = current_user()
        if user is None:
            if "/api/" in request.path:
                return jsonify(error="Sign in required"), 401
            target = request.full_path.rstrip("?") if request.method == "GET" else None
            return redirect(url_for("auth.login", next=target))

        if endpoint.startswith("upload.") and not user.is_admin:
            abort(403)
        return None

    @app.context_processor
    def inject_user():
        return {"current_user": current_user()}

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("forbidden.html"), 403

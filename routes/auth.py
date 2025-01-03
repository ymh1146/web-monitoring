from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from functools import wraps
from core.database import get_auth_config
from werkzeug.security import check_password_hash
import time

auth_bp = Blueprint("auth", __name__)


def chk_auth_st():
 
    login_t = session.get("login_t")
    if not login_t:
        return False

    if time.time() - login_t > 24 * 3600:
        session.pop("login_t", None)
        return False

    return True


def verify_pwd(pwd):

    auth_cfg = get_auth_config()

    if not pwd:
        return False

    if not auth_cfg.get("pwd_hash"):
        return False
 
    return check_password_hash(auth_cfg["pwd_hash"], pwd)


def is_auth(req_login=True):

    auth_cfg = get_auth_config()
 
    if chk_auth_st():
        return True

    if req_login:
        return False

    return not auth_cfg["req_pwd"]


def login_req(func=None, *, req_login=True):
 
    def actual_decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not is_auth(req_login=req_login):
                next_p = request.path
                return redirect(url_for("auth.login", next=next_p))
            return f(*args, **kwargs)
        return wrapper
    
    if func:
        return actual_decorator(func)
    return actual_decorator


@auth_bp.route("/")
def index():
    if not is_auth(req_login=False):
        return redirect(url_for("auth.login"))
    return redirect(url_for("monitor.st_page"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    next_p = request.args.get("next")

    if chk_auth_st():
        return redirect(next_p if next_p else url_for("monitor.st_page"))

    if request.method == "POST":
        pwd = request.form.get("pwd")

        if not verify_pwd(pwd):
            flash("密码错误" if pwd else "请输入密码")
            return render_template("login.html")

        session["login_t"] = time.time()
        return redirect(next_p if next_p else url_for("monitor.st_page"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.pop("login_t", None)
    return redirect(url_for("auth.login"))

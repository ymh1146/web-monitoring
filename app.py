from flask import (
    Flask,
    render_template,
    redirect,
    request,
    session,
    url_for,
    send_from_directory,
    flash,
)
from core.database import init_db, clear_all_data
from core.monitor import record_status
from core.scheduler import start_sched
from visualization.charts import gen_all_charts
from utils.logger import log_msg
from config.auth_settings import load_auth_cfg, save_auth_cfg, verify_password
from config.website_manager import load_sites, save_sites
import time
import os
from threading import Thread
from datetime import datetime, timedelta
import json

app = Flask(
    __name__,
    static_folder="static",
    template_folder=os.path.join("visualization", "templates"),
)
app.secret_key = os.urandom(24)


# 登录有效期1小时
def check_auth_status():
    if not session.get("auth"):
        return False

    login_time = session.get("login_time")
    if not login_time:
        return False

    login_time = datetime.fromtimestamp(login_time)
    if datetime.now() - login_time > timedelta(hours=1):
        session.clear()
        return False

    return True


def is_auth(require_login=False):

    auth_cfg = load_auth_cfg()

    if require_login:
        return check_auth_status()

    if not auth_cfg["req_pwd"]:
        return True
    return check_auth_status()


@app.route("/")
def index():

    next_page = request.args.get("next")

    if next_page == "settings":
        return render_template("login.html")

    if is_auth():
        return redirect(url_for("status"))

    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():

    if verify_password(request.form["pwd"]):
        session["auth"] = True
        session["login_time"] = datetime.now().timestamp()
        next_page = request.args.get("next")
        return redirect(url_for("settings" if next_page == "settings" else "status"))

    flash("密码错误")
    return render_template("login.html")


@app.route("/status")
def status():

    if not is_auth():
        return redirect(url_for("index"))

    try:

        status_file = os.path.join("static", "status.html")
        if not os.path.exists(status_file):
            flash("状态页面未生成，请先更新图表")
            return redirect(url_for("settings"))

        with open(status_file, "r", encoding="utf-8") as f:
            content = f.read()

        response = app.make_response(content)
        response.headers["Content-Type"] = "text/html; charset=utf-8"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    except Exception as e:
        log_msg(f"加载状态页面时出错: {str(e)}")
        flash("加载状态页面时出错，请重试")
        return redirect(url_for("settings"))


@app.route("/settings")
def settings():

    if not is_auth(require_login=True):
        flash("请先登录")
        return redirect(url_for("index", next="settings"))

    auth_cfg = load_auth_cfg()
    websites = load_sites()
    return render_template(
        "settings.html", require_password=auth_cfg["req_pwd"], websites=websites
    )


@app.route("/update_settings", methods=["POST"])
def update_settings():

    if not is_auth(require_login=True):
        return redirect(url_for("index"))

    try:
        auth_cfg = load_auth_cfg()
        auth_cfg["req_pwd"] = request.form.get("require_password") == "true"
        if request.form.get("password"):
            auth_cfg["pwd"] = request.form["password"]
        save_auth_cfg(auth_cfg)

        # 处理网站配置
        websites = []
        urls = request.form.getlist("websites[][url]")
        notes = request.form.getlist("websites[][note]")
        request_bodies = request.form.getlist("websites[][request_body]")
        request_headers = request.form.getlist("websites[][request_headers]")
        
        for i in range(len(urls)):
            if urls[i].strip():
                try:
                    headers = json.loads(request_headers[i]) if i < len(request_headers) and request_headers[i].strip() else {}
                except json.JSONDecodeError:
                    headers = {}
                    
                websites.append({
                    "url": urls[i],
                    "note": notes[i] if i < len(notes) else "",
                    "request_body": request_bodies[i] if i < len(request_bodies) else "",
                    "request_headers": headers
                })
        
        if websites:
            save_sites(websites)
            flash("设置已保存")
        else:
            flash("请至少添加一个监控点")

        return redirect(url_for("settings"))
    except Exception as e:
        log_msg(f"保存设置时出错: {str(e)}")
        flash("保存设置时出错，请重试")
        return redirect(url_for("settings"))


@app.route("/update_charts")
def update_charts():

    if not is_auth(require_login=True):
        return redirect(url_for("index"))

    try:
        record_status()
        gen_all_charts()
        flash("图表已更新")
    except Exception as e:
        log_msg(f"更新图表时出错: {str(e)}")
        flash("更新图表时出错，请重试")

    return redirect(url_for("status"))


def update_mon_data():

    with app.app_context():
        try:
            record_status()
            gen_all_charts()
            log_msg("监控数据和图表已更新")
        except Exception as e:
            log_msg(f"更新监控数据时出错: {str(e)}")


@app.route("/logout")
def logout():

    session.clear()
    return redirect(url_for("index"))


def init_mon():

    log_msg("开始初始化监控...")
    init_db()

    sites = load_sites()
    if sites:
        log_msg("执行首次监测...")
        record_status()

    log_msg("生成首次图表...")
    gen_all_charts()
    log_msg("初始化完成")


if __name__ == "__main__":

    with app.app_context():
        init_mon()

    sched_runner = start_sched(app)
    sched_thread = Thread(target=sched_runner)
    sched_thread.daemon = True
    sched_thread.start()

    log_msg("启动 Web 服务...")

    app.run(host="0.0.0.0", port=5000)

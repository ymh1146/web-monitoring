from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    request,
    flash,
    jsonify,
    session,
)
from routes.auth import login_req, is_auth
from core.database import (
    get_st,
    get_auth_config,
    get_push_config,
    save_auth_config,
    save_st_cfg,
    clear_data,
)
from config.settings import MON_INTV, CHART_UPD_INTV, FAV_REF_H
import os
import re
from utils.logger import log
import json
import traceback
import time

set_bp = Blueprint("settings", __name__)


@set_bp.route("/settings")
@login_req(req_login=True)
def set_page():
    sites = get_st()
    auth_cfg = get_auth_config()
    push_cfg = get_push_config()

    if push_cfg:
        push_cfg = {
            "wechat": {
                "enabled": push_cfg.get("wechat", {}).get("enabled", False),
                "webhook": push_cfg.get("wechat", {}).get("webhook", ""),
            },
            "serverchan": {
                "enabled": push_cfg.get("serverchan", {}).get("enabled", False),
                "send_key": push_cfg.get("serverchan", {}).get("send_key", ""),
            },
            "pushplus": {
                "enabled": push_cfg.get("pushplus", {}).get("enabled", False),
                "token": push_cfg.get("pushplus", {}).get("token", ""),
            },
            "telegram": {
                "enabled": push_cfg.get("telegram", {}).get("enabled", False),
                "bot_token": push_cfg.get("telegram", {}).get("bot_token", ""),
                "chat_id": push_cfg.get("telegram", {}).get("chat_id", ""),
                "proxy": push_cfg.get("telegram", {}).get("proxy", ""),
            },
            "email": {
                "enabled": push_cfg.get("email", {}).get("enabled", False),
                "smtp_server": push_cfg.get("email", {}).get("smtp_server", ""),
                "smtp_port": push_cfg.get("email", {}).get("smtp_port", 465),
                "username": push_cfg.get("email", {}).get("username", ""),
                "password": push_cfg.get("email", {}).get("password", ""),
                "to_addr": push_cfg.get("email", {}).get("to_addr", ""),
            },
            "custom": {
                "enabled": push_cfg.get("custom", {}).get("enabled", False),
                "name": push_cfg.get("custom", {}).get("name", ""),
                "url": push_cfg.get("custom", {}).get("url", ""),
                "method": push_cfg.get("custom", {}).get("method", "POST"),
                "headers": push_cfg.get("custom", {}).get("headers", "{}"),
                "body_tpl": push_cfg.get("custom", {}).get("body_tpl", "{}"),
                "timeout": push_cfg.get("custom", {}).get("timeout", 10)
            }
        }
    else:
        push_cfg = {}

    return render_template(
        "settings.html",
        sites=sites,
        mon_intv=MON_INTV,
        chart_upd_intv=CHART_UPD_INTV,
        fav_ref_h=FAV_REF_H,
        req_pwd=auth_cfg["req_pwd"],
        push_config=push_cfg,
    )


@set_bp.route("/save_system_settings", methods=["POST"])
@login_req(req_login=True)
def save_sys_set():
    try:
        set_path = os.path.join("config", "settings.py")
        with open(set_path, "r", encoding="utf-8") as f:
            content = f.read()

        mon_intv = request.form.get("mon_intv", type=int)
        chart_upd_intv = request.form.get("chart_upd_intv", type=int)
        fav_ref_h = request.form.get("fav_ref_h", type=int)

        content = re.sub(r"MON_INTV\s*=\s*\d+", f"MON_INTV = {mon_intv}", content)
        content = re.sub(
            r"CHART_UPD_INTV\s*=\s*\d+", f"CHART_UPD_INTV = {chart_upd_intv}", content
        )
        content = re.sub(r"FAV_REF_H\s*=\s*\d+", f"FAV_REF_H = {fav_ref_h}", content)

        with open(set_path, "w", encoding="utf-8") as f:
            f.write(content)

        global MON_INTV, CHART_UPD_INTV, FAV_REF_H
        MON_INTV = mon_intv
        CHART_UPD_INTV = chart_upd_intv
        FAV_REF_H = fav_ref_h

        flash("系统设置已保存")
        return redirect(url_for("settings.set_page"))

    except Exception as e:
        flash(f"保存系统设置失败: {str(e)}")
        return redirect(url_for("settings.set_page"))


@set_bp.route("/update_settings", methods=["POST"])
@login_req(req_login=True)
def upd_set():
    try:
        req_pwd = request.form.get("req_pwd") == "true"
        pwd = request.form.get("pwd")
        if save_auth_config(req_pwd, pwd if pwd else None):
            flash("密码设置已更新")

            session["login_t"] = time.time()
        else:
            flash("保存设置失败，请重试")

    except Exception as e:
        log(f"保存设置时出错: {str(e)}")
        flash(f"保存设置时出错: {str(e)}")

    return redirect(url_for("settings.set_page"))


@set_bp.route("/clear_data")
@login_req(req_login=True)
def clear_data():
    try:
        clear_data()

        fav_dir = os.path.join("static", "favicons")
        if os.path.exists(fav_dir):
            for file in os.listdir(fav_dir):
                file_path = os.path.join(fav_dir, file)
                try:
                    os.remove(file_path)
                except:
                    pass

        st_file = os.path.join("static", "status.html")
        if os.path.exists(st_file):
            os.remove(st_file)

        flash("所有数据已清空")
    except Exception as e:
        log(f"清空数据时出错: {str(e)}")
        flash("清空数据时出错，请重试")

    return redirect(url_for("settings.set_page"))


def fmt_json(in_str):

    try:

        in_str = in_str.strip()
        if not in_str:
            return "{}"

        in_str = in_str.replace("'", '"')

        json_obj = json.loads(in_str)

        return json.dumps(json_obj, ensure_ascii=False, separators=(",", ":"))

    except json.JSONDecodeError:
        return "{}"


@set_bp.route("/save_sites", methods=["POST"])
def save_st_hdl():
    try:
        urls = request.form.getlist("urls[]")
        notes = request.form.getlist("notes[]")
        hdrs = request.form.getlist("hdrs[]")
        body = request.form.getlist("body[]")
        expire_dates = request.form.getlist("expire_date[]")

        sites = []
        for i in range(len(urls)):
            if not urls[i]:
                continue

            site = {
                "url": urls[i],
                "note": notes[i] if i < len(notes) else "",
                "req_hdrs": hdrs[i] if i < len(hdrs) else "",
                "req_body": body[i] if i < len(body) else "",
                "expire_date": expire_dates[i] if i < len(expire_dates) else "",
            }
            sites.append(site)

        if save_st_cfg(sites):
            flash("保存成功")
        else:
            flash("保存失败")

    except Exception as e:
        log(f"保存网站设置失败: {str(e)}")
        flash("保存失败")

    return redirect(url_for("settings.set_page"))

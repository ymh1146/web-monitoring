from flask import Blueprint, jsonify, request, flash, redirect, url_for
from routes.auth import login_req
from core.database import get_push_config, save_push_config
from utils.logger import log

push_bp = Blueprint("push", __name__)


@push_bp.route("/get_push_config")
@login_req(req_login=True)
def get_push_cfg_hdl():

    cfg = get_push_config()
    return jsonify(cfg)


@push_bp.route("/save_push_config", methods=["POST"])
@login_req(req_login=True)
def save_push_cfg_hdl():

    try:
        push_cfg = {
            "wechat": {
                "enabled": request.form.get("wechat.enabled") == "on",
                "hook": request.form.get("wechat.webhook", "").strip(),
            },
            "serverchan": {
                "enabled": request.form.get("serverchan.enabled") == "on",
                "key": request.form.get("serverchan.send_key", "").strip(),
            },
            "pushplus": {
                "enabled": request.form.get("pushplus.enabled") == "on",
                "token": request.form.get("pushplus.token", "").strip(),
            },
            "telegram": {
                "enabled": request.form.get("telegram.enabled") == "on",
                "token": request.form.get("telegram.bot_token", "").strip(),
                "chat": request.form.get("telegram.chat_id", "").strip(),
                "proxy": request.form.get("telegram.proxy", "").strip(),
            },
            "email": {
                "enabled": request.form.get("email.enabled") == "on",
                "smtp_srv": request.form.get("email.smtp_server", "").strip(),
                "smtp_prt": int(request.form.get("email.smtp_port", 465)),
                "user": request.form.get("email.username", "").strip(),
                "pwd": request.form.get("email.password", "").strip(),
                "to": request.form.get("email.to_addr", "").strip(),
            },
            "custom": {
                "enabled": request.form.get("custom.enabled") == "on",
                "name": request.form.get("custom.name", "").strip(),
                "url": request.form.get("custom.url", "").strip(),
                "method": request.form.get("custom.method", "POST").strip(),
                "headers": request.form.get("custom.headers", "{}").strip(),
                "body_tpl": request.form.get("custom.body_tpl", "{}").strip(),
                "timeout": int(request.form.get("custom.timeout", 10))
            }
        }

        save_push_config(push_cfg)
        flash("推送配置已保存")

    except Exception as e:
        log(f"保存推送配置失败: {str(e)}")
        flash(f"保存推送配置失败: {str(e)}")

    return redirect(url_for("settings.set_page"))

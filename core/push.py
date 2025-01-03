import requests
from utils.logger import log
import json
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from core.database import get_push_config
from core.utils import norm_url


def push_wx(title, content, cfg):
    try:
        # 兼容新旧字段名
        hook = cfg.get("hook") or cfg.get("webhook")
        if not hook:
            log("企业微信Webhook未配置")
            return

        data = {
            "msgtype": "markdown",
            "markdown": {"content": f"### {title}\n{content}"},
        }

        r = requests.post(hook, json=data, timeout=5)

        if r.status_code != 200:
            log(f"企业微信推送失败: {r.text}")
            return

        result = r.json()
        if result["errcode"] != 0:
            log(f"企业微信推送失败: {result['errmsg']}")
            return

        log("企业微信推送成功")

    except Exception as e:
        log(f"企业微信推送出错: {str(e)}")


def push_sc(title, content, cfg):
    try:
        # 兼容新旧字段名
        key = cfg.get("key") or cfg.get("send_key")
        if not key:
            log("Server酱SendKey未配置")
            return

        r = requests.post(
            f"https://sctapi.ftqq.com/{key}.send",
            data={"title": title, "desp": content},
            timeout=5,
        )

        if r.status_code != 200:
            log(f"Server酱推送失败: {r.text}")
            return

        result = r.json()
        if result["code"] != 0:
            log(f"Server酱推送失败: {result['message']}")
            return

        log("Server酱推送成功")

    except Exception as e:
        log(f"Server酱推送出错: {str(e)}")


def push_pp(title, content, cfg):
    try:
        token = cfg.get("token")
        if not token:
            log("PushPlus token未配置")
            return

        r = requests.post(
            "http://www.pushplus.plus/send",
            json={
                "token": token,
                "title": title,
                "content": content,
                "template": "markdown",
            },
            timeout=5,
        )

        if r.status_code != 200:
            log(f"PushPlus推送失败: {r.text}")
            return

        result = r.json()
        if result["code"] != 200:
            log(f"PushPlus推送失败: {result['msg']}")
            return

        log("PushPlus推送成功")

    except Exception as e:
        log(f"PushPlus推送出错: {str(e)}")


def push_tg(title, content, cfg):
    try:
        # 兼容新旧字段名
        token = cfg.get("token") or cfg.get("bot_token")
        chat = cfg.get("chat") or cfg.get("chat_id")
        proxy = cfg.get("proxy")

        if not token or not chat:
            log("Telegram配置不完整")
            return

        proxies = None
        if proxy:
            proxies = {"http": proxy, "https": proxy}

        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat,
                "text": f"*{title}*\n\n{content}",
                "parse_mode": "Markdown",
            },
            proxies=proxies,
            timeout=5,
        )

        if r.status_code != 200:
            log(f"Telegram推送失败: {r.text}")
            return

        result = r.json()
        if not result["ok"]:
            log(f"Telegram推送失败: {result['description']}")
            return

        log("Telegram推送成功")

    except Exception as e:
        log(f"Telegram推送出错: {str(e)}")


def push_mail(title, content, cfg):
    try:
        # 兼容新旧字段名
        smtp_srv = cfg.get("smtp_srv") or cfg.get("smtp_server")
        smtp_prt = cfg.get("smtp_prt") or cfg.get("smtp_port")
        user = cfg.get("user") or cfg.get("username")
        pwd = cfg.get("pwd") or cfg.get("password")
        to = cfg.get("to") or cfg.get("to_addr")

        if not all([smtp_srv, smtp_prt, user, pwd, to]):
            log("邮件配置不完整")
            return

        msg = MIMEText(content, "plain", "utf-8")
        msg["From"] = Header(user)
        msg["To"] = Header(to)
        msg["Subject"] = Header(title)

        with smtplib.SMTP_SSL(smtp_srv, smtp_prt) as server:
            server.login(user, pwd)
            server.sendmail(user, to, msg.as_string())

        log("邮件推送成功")

    except Exception as e:
        log(f"邮件推送出错: {str(e)}")


def send_msg(title, content, push_cfg=None):
    if not push_cfg:
        from core.database import get_push_config

        push_cfg = get_push_config()

    if not push_cfg:
        return

    for push_type, cfg in push_cfg.items():
        if not cfg.get("enabled", False):
            continue

        try:
            if push_type == "wechat":
                push_wx(title, content, cfg)
            elif push_type == "serverchan":
                push_sc(title, content, cfg)
            elif push_type == "pushplus":
                push_pp(title, content, cfg)
            elif push_type == "telegram":
                push_tg(title, content, cfg)
            elif push_type == "email":
                push_mail(title, content, cfg)
        except Exception as e:
            log(f"{push_type} 推送失败: {str(e)}")
            continue


def check_domain_expire():

    from core.database import get_st
    from datetime import datetime

    is_first_run = not hasattr(check_domain_expire, "last_check_date")

    now = datetime.now()
    current_date = now.date()

    # 首次运行推送，每日10点定时推送
    if not is_first_run:

        if now.hour != 10 or current_date == check_domain_expire.last_check_date:
            return

    sites = get_st()
    if not sites:
        return

    check_domain_expire.last_check_date = current_date

    expiring_domains = []
    for site in sites:
        if not site.get("expire_date"):
            continue

        try:
            expire_date = datetime.strptime(site["expire_date"], "%Y-%m-%d")
            days_left = (expire_date.date() - current_date).days
            url = site["url"]
            disp_url = norm_url(url)

            if days_left <= 30:
                expiring_domains.append({"url": disp_url, "days": days_left})
        except Exception as e:
            log(f"检查域名 {site['url']} 到期状态时出错: {str(e)}")
            continue

    if expiring_domains:
        title = "域名到期提醒"
        content = "以下域名即将到期：\n\n"
        for domain in expiring_domains:
            content += f"• {domain['url']} - 剩余 {domain['days']} 天\n"
        content += "\n请及时续费！"

        send_msg(title, content)
        log("已发送域名到期提醒通知")

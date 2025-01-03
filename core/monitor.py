import json
import time
import requests
import urllib3
import os
import random
import threading
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from datetime import datetime
from config.settings import FAV_REF_H, CDN_ERR
from core.database import save_st_rec, get_st
from utils.logger import log, log_err, log_mon
from core.push import send_msg


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 增加状态锁，防止多进程启动
_st_chk_lock = threading.Lock()
_last_chk = 0
MIN_CHK_INTV = 5


def get_rand_hdrs(url):

    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower()

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Edge/120.0.0.0",
    ]

    hdrs = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": random.choice(user_agents),
        "Host": domain,
        "Referer": f"{parsed_url.scheme}://{domain}/",
        "DNT": "1",
        "Pragma": "no-cache",
    }

    return {k: v for k, v in hdrs.items() if v}


def down_fav(url):

    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        if not domain:
            return None

        fav_dir = os.path.join("static", "favicons")
        os.makedirs(fav_dir, exist_ok=True)

        fav_name = f"{domain.replace(':', '_')}.ico"
        fav_path = os.path.join(fav_dir, fav_name)
        rel_path = os.path.join("favicons", fav_name)

        if os.path.exists(fav_path):
            mtime = os.path.getmtime(fav_path)
            if time.time() - mtime < FAV_REF_H * 3600:
                return rel_path

        # 简化获取ico流程，直接硬性匹配地址，没有则无
        favicon_paths = [
            "/favicon.ico",
            "/static/favicon.ico",
            "/assets/favicon.ico",
            "/images/favicon.ico",
            "/img/favicon.ico",
            "/static/images/favicon.ico",
            "/static/img/favicon.ico",
            "/assets/images/favicon.ico",
            "/public/favicon.ico",
        ]

        for fav_path in favicon_paths:
            try:
                host_url = f"{parsed.scheme}://{domain}{fav_path}"
                response = requests.get(host_url, timeout=5, verify=False)

                if response.status_code == 200 and len(response.content) > 0:
                    with open(os.path.join(fav_dir, fav_name), "wb") as f:
                        f.write(response.content)
                    return rel_path
            except:
                continue

        return None

    except Exception as e:
        log_err(f"下载favicon.ico失败 ({domain}): {str(e)}")
        return None


def rec_st(site):

    hdrs = {}
    max_retry = 3  # 检查网站状态最大重试次数
    retry_cnt = 0
    last_err = None
    req_hdrs = None
    cur_status = None

    last_status = getattr(rec_st, f"last_status_{site['url']}", None)

    while retry_cnt < max_retry:
        try:
            hdrs = get_rand_hdrs(site["url"])

            if "req_hdrs" in site and site["req_hdrs"] and site["req_hdrs"] != "{}":
                try:
                    custom_hdrs = json.loads(site["req_hdrs"])
                    if isinstance(custom_hdrs, dict) and custom_hdrs:
                        hdrs.update(custom_hdrs)
                        log(f"合并自定义请求头: {site['url']}")
                except json.JSONDecodeError:
                    log_err(f"请求头解析失败: {site['req_hdrs']}")
                except Exception as e:
                    log_err(f"处理请求头时出错: {str(e)}")

            req_hdrs = hdrs.copy()

            req_kwargs = {
                "headers": hdrs,
                "timeout": 10,
                "verify": False,
                "allow_redirects": True,
            }

            req_body = site.get("req_body", "").strip()
            if req_body:
                try:
                    json_body = json.loads(req_body)
                    if not isinstance(json_body, dict):
                        raise ValueError("请求体必须是JSON对象")

                    hdrs["Content-Type"] = "application/json"
                    req_hdrs = hdrs.copy()
                    response = requests.post(site["url"], json=json_body, **req_kwargs)
                except (json.JSONDecodeError, ValueError) as e:
                    err_msg = f"请求体格式错误: {str(e)}"
                    log_err(
                        f"""
请求体解析失败 - {site['url']}
备注: {site.get('note', '无')}
请求体: {req_body}
错误信息: {err_msg}
请求头: {req_hdrs}
{'=' * 80}"""
                    )
                    cur_status = (-1, err_msg)
                    save_st_rec(site["url"], -1, err_msg, None)

                    send_msg(
                        f"监控异常 - {site.get('note', site['url'])}",
                        f"网站: {site['url']}\n状态: 请求体格式错误\n错误信息: {err_msg}",
                    )
                    return cur_status
            else:
                response = requests.get(site["url"], **req_kwargs)

            st_code = response.status_code
            err_msg = ""

            if st_code != 200:
                err_msg = f"HTTP {st_code}"

                if response.text:
                    for key in CDN_ERR:
                        if key.lower() in response.text.lower():
                            err_msg = f"CDN错误: {key}"
                            break

                if st_code in [400, 401, 403, 404, 405]:
                    log_err(
                        f"""
监控异常（不重试） - {site['url']}
备注: {site.get('note', '无')}
状态码: {st_code}
错误信息: {err_msg}
响应头: {dict(response.headers)}
响应内容: {response.text[:500]}...
请求信息:
  方法: {'POST' if req_body else 'GET'}
  请求头: {req_hdrs}
  请求体: {req_body if req_body else '无'}
{'=' * 80}"""
                    )
                    cur_status = (st_code, err_msg)

                    send_msg(
                        f"监控异常 - {site.get('note', site['url'])}",
                        f"网站: {site['url']}\n状态码: {st_code}\n错误信息: {err_msg}",
                    )
                    break

                last_err = err_msg
                retry_cnt += 1
                if retry_cnt < max_retry:
                    log(
                        f"请求失败，将在1秒后进行第{retry_cnt + 1}次重试: {site['url']}"
                    )
                    time.sleep(1)
                    continue
            else:
                cur_status = (200, "")

                if last_status is not None and last_status[0] != 200:
                    send_msg(
                        f"监控恢复 - {site.get('note', site['url'])}",
                        f"网站: {site['url']}\n状态: 已恢复正常访问",
                    )
                break

        except requests.RequestException as e:
            last_err = f"请求错误: {str(e)}"
            retry_cnt += 1
            if retry_cnt < max_retry:
                log(f"请求异常，将在1秒后进行第{retry_cnt + 1}次重试: {site['url']}")
                time.sleep(1)
                continue
            err_msg = last_err
            st_code = -1
            cur_status = (st_code, err_msg)

            send_msg(
                f"监控异常 - {site.get('note', site['url'])}",
                f"网站: {site['url']}\n状态: 请求失败\n错误信息: {err_msg}",
            )
            break

    if cur_status is None:
        cur_status = (-1, last_err or "未知错误")

        send_msg(
            f"监控异常 - {site.get('note', site['url'])}",
            f"网站: {site['url']}\n状态: 重试失败\n错误信息: {last_err or '未知错误'}",
        )

    fav_path = None
    if cur_status[0] == 200:
        fav_path = down_fav(site["url"])

    save_st_rec(site["url"], cur_status[0], cur_status[1], fav_path)
    log_mon(site["url"], cur_status[0], cur_status[1])

    setattr(rec_st, f"last_status_{site['url']}", cur_status)

    return cur_status


def rec_all_st():

    global _last_chk

    now = time.time()

    if _last_chk > 0 and now - _last_chk < MIN_CHK_INTV * 60:
        return

    if not _st_chk_lock.acquire(blocking=False):
        return

    try:
        sites = get_st()
        if not sites:
            return

        for site in sites:
            try:
                rec_st(site)
            except Exception as e:
                log(f"检查网站 {site['url']} 状态时出错: {str(e)}")

        log("完成一次状态检查")

        _last_chk = now

    finally:
        _st_chk_lock.release()

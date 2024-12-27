import requests
import json
from config.settings import CDN_ERR_KEYS
from config.website_manager import load_sites
from core.database import save_status
from utils.logger import log_msg


def check_site_status(site):
    """检查网站状态
    
    Args:
        site: 网站配置字典，包含url、note、request_body和request_headers
    """
    url = site["url"]
    request_body = site.get("request_body", "").strip()
    
    # 合并默认请求头和自定义请求头
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json"
    }
    custom_headers = site.get("request_headers", {})
    headers.update(custom_headers)
    
    try:
        if request_body:
            try:
                body = json.loads(request_body)
                resp = requests.post(url, json=body, headers=headers, timeout=20)
            except json.JSONDecodeError as e:
                return f"请求体JSON格式错误: {str(e)}"
            except requests.exceptions.RequestException as e:
                error_msg = str(e)
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        error_detail = e.response.json().get('message', e.response.text[:200])
                    except:
                        error_detail = e.response.text[:200] if e.response.text else error_msg
                    return f"Error {e.response.status_code}: {error_detail}"
                return f"Error: {error_msg}"
        else:
            try:
                resp = requests.get(url, headers=headers, timeout=20)
            except requests.exceptions.RequestException as e:
                error_msg = str(e)
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        error_detail = e.response.json().get('message', e.response.text[:200])
                    except:
                        error_detail = e.response.text[:200] if e.response.text else error_msg
                    return f"Error {e.response.status_code}: {error_detail}"
                return f"Error: {error_msg}"
            
        if any(err in resp.text for err in CDN_ERR_KEYS):
            return "CDN Error Page"
        elif resp.status_code == 200:
            return "OK"
        else:
            try:
                error_detail = resp.json().get('message', '')
            except:
                error_detail = resp.text[:200] if resp.text else ''
            
            if error_detail:
                # 尝试提取更多错误信息
                error_info = []
                try:
                    error_json = resp.json()
                    if 'code' in error_json:
                        error_info.append(f"code={error_json['code']}")
                    if 'error' in error_json:
                        error_info.append(error_json['error'])
                    if 'message' in error_json:
                        error_info.append(error_json['message'])
                except:
                    error_info.append(error_detail)
                
                return f"Error {resp.status_code}: {' | '.join(error_info)}"
            return f"Error {resp.status_code}: {resp.reason}"
            
    except requests.exceptions.Timeout:
        return "Error: 连接超时 (20s)"
    except requests.exceptions.ConnectionError as e:
        if "Connection refused" in str(e):
            return "Error: 连接被拒绝"
        elif "Name or service not known" in str(e):
            return "Error: DNS解析失败"
        elif "Connection reset by peer" in str(e):
            return "Error: 连接被重置"
        return f"Error: 连接错误 - {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


def record_status():
    """记录所有网站状态"""
    sites = load_sites()
    for site in sites:
        status = check_site_status(site)
        save_status(site["url"], status)
        if status != "OK":
            note = site.get("note", "").strip()
            site_desc = f"{site['url']}" + (f" ({note})" if note else "")
            log_msg(f"网站 {site_desc} 状态异常: {status}")

    log_msg("完成一次状态检查")

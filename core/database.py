import sqlite3
import json
import os
from datetime import datetime, timedelta
from utils.logger import log
from config.settings import ST_CODE, CLR_CODE, ST_TEXT, REV_ST_CODE, VERSION
from werkzeug.security import generate_password_hash
import traceback


def get_db():
    data_dir = "data"
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "mon.db")


def init_db():
    try:
        conn = sqlite3.connect(get_db())
        c = conn.cursor()

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS sites (
                url TEXT PRIMARY KEY,
                note TEXT,
                req_hdrs TEXT,
                req_body TEXT,
                sort_order INTEGER DEFAULT 0,
                expire_date TEXT
            )
        """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS status_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                st_code TEXT,
                err_msg TEXT,
                fav_path TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS push_config (
                id INTEGER PRIMARY KEY,
                config TEXT NOT NULL
            )
        """
        )

        c.execute("SELECT value FROM system_config WHERE key = 'db_version'")
        if not c.fetchone():
         
            c.execute(
                "INSERT INTO system_config (key, value) VALUES (?, ?)",
                ("db_version", "1.4")
            )

            c.execute(
                "INSERT INTO system_config (key, value) VALUES (?, ?)",
                ("pwd_h", generate_password_hash("admin"))
            )

            c.execute(
                "INSERT INTO system_config (key, value) VALUES (?, ?)",
                ("req_pwd", "1")
            )
            log(f"初始化数据库完成，版本 1.4")

        conn.commit()
        conn.close()

    except Exception as e:
        log(f"初始化数据库失败: {str(e)}")
        if conn:
            conn.close()


init_db()


def enc_status(code, err_msg=""):

    if code == 200:
        return ST_CODE[200]
    elif "CDN误" in err_msg:
        return ST_CODE["CDN"]
    elif code == 404:
        return ST_CODE[404]
    elif code == 500:
        return ST_CODE[500]
    elif code == -1:
        return ST_CODE[-1]
    else:
        return ST_CODE[-1]


def dec_status(encoded):

    if encoded in REV_ST_CODE:
        code = REV_ST_CODE[encoded]
        if isinstance(code, int):
            return code, f"HTTP {code}" if code != 200 else ""
        elif code == "CDN":
            return -1, "CDN错误"
        else:
            return -1, "未知错误"
    return -1, "未知错误"


def save_st_rec(url, st_code, err_msg="", fav_path=None):

    try:
        conn = sqlite3.connect(get_db())
        c = conn.cursor()

        enc_st = enc_status(st_code, err_msg)

        c.execute(
            """
            INSERT INTO status_records 
            (url, st_code, err_msg, fav_path, timestamp) 
            VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
        """,
            (url, enc_st, err_msg, fav_path),
        )

        ago30 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        c.execute(
            "DELETE FROM status_records WHERE timestamp < datetime(?, 'localtime')",
            (ago30,),
        )

        conn.commit()
        conn.close()

    except Exception as e:
        log(f"保存状态数据出错: {str(e)}")


def get_st_data(hours=24):

    try:
        conn = sqlite3.connect(get_db())
        c = conn.cursor()

        time_limit = (datetime.now() - timedelta(hours=hours)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        c.execute(
            """
            SELECT url, st_code, err_msg, fav_path, timestamp 
            FROM status_records 
            WHERE timestamp > datetime(?, 'localtime')
            ORDER BY timestamp ASC
        """,
            (time_limit,),
        )

        records = c.fetchall()
        conn.close()

        data = {}
        for record in records:
            url = record[0]
            if url not in data:
                data[url] = {
                    "timestamps": [],
                    "st_codes": [],
                    "err_msgs": [],
                    "fav_path": record[3],
                }

            st_code, err_msg = dec_status(record[1])
            data[url]["timestamps"].append(record[4])
            data[url]["st_codes"].append(st_code)
            data[url]["err_msgs"].append(err_msg or record[2])

        return data

    except Exception as e:
        log(f"获取状态数据出错: {str(e)}")
        return {}


def clear_data():

    conn = sqlite3.connect(get_db())
    c = conn.cursor()
    c.execute("DELETE FROM status_records")
    conn.commit()
    conn.close()
    log("已清空所有监控数据")


def save_st_cfg(sites):

    try:
        conn = sqlite3.connect(get_db())
        c = conn.cursor()

        c.execute("DELETE FROM sites")

        for i, site in enumerate(sites, 1):
            c.execute(
                "INSERT INTO sites (url, note, req_hdrs, req_body, sort_order, expire_date) VALUES (?, ?, ?, ?, ?, ?)",
                (site["url"], site["note"], site["req_hdrs"], site["req_body"], i, site.get("expire_date", "")),
            )

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        log(f"保存网站列表失败: {str(e)}")
        return False


def get_st():
    try:
        conn = sqlite3.connect(get_db())
        c = conn.cursor()

        try:
            c.execute("SELECT url, note, req_hdrs, req_body, expire_date FROM sites ORDER BY sort_order")
        except sqlite3.OperationalError:
            # 如果 expire_date 列不存在，使用旧的查询
            c.execute("SELECT url, note, req_hdrs, req_body FROM sites ORDER BY sort_order")
            
        rows = c.fetchall()
        conn.close()

        sites = []
        for row in rows:
            try:
                site = {
                    "url": row[0],
                    "note": row[1] if row[1] else "",
                    "req_hdrs": row[2] if row[2] else "{}",
                    "req_body": row[3] if row[3] else "",
                }
                if len(row) > 4:  
                    site["expire_date"] = row[4] if row[4] else ""
                sites.append(site)
            except json.JSONDecodeError:
                site = {
                    "url": row[0],
                    "note": row[1] if row[1] else "",
                    "req_hdrs": "{}",
                    "req_body": row[3] if row[3] else "",
                }
                if len(row) > 4:  
                    site["expire_date"] = row[4] if row[4] else ""
                sites.append(site)

        return sites

    except Exception as e:
        if not str(e).startswith("no such column"): 
            log(f"获取网站列表失败: {str(e)}")
        return []


def save_auth_config(require_password=False, password=None):

    try:
        conn = sqlite3.connect(get_db())
        c = conn.cursor()

        c.execute(
            "INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)",
            ("req_pwd", "1" if require_password else "0"),
        )

        if password is not None:

            password_hash = generate_password_hash(password)
            c.execute(
                "INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)",
                ("pwd_h", password_hash),
            )

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log(f"保存认证配置出错: {str(e)}")
        return False


def get_auth_config():

    try:
        conn = sqlite3.connect(get_db())
        c = conn.cursor()

        c.execute(
            "SELECT key, value FROM system_config WHERE key IN ('req_pwd', 'pwd_h')"
        )
        config = dict(c.fetchall())

        conn.close()
        return {
            "req_pwd": config.get("req_pwd") == "1",
            "pwd_hash": config.get("pwd_h", ""),
        }
    except Exception as e:
        log(f"获取认证配置出错: {str(e)}")
        return {"req_pwd": False, "pwd_hash": ""}


def save_push_config(config):

    try:
        conn = sqlite3.connect(get_db())
        c = conn.cursor()

        c.execute(
            "INSERT OR REPLACE INTO push_config (id, config) VALUES (1, ?)",
            (json.dumps(config),),
        )

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        log(f"保存推送配置失败: {str(e)}")
        return False


def get_push_config():

    try:
        conn = sqlite3.connect(get_db())
        c = conn.cursor()

        c.execute("SELECT config FROM push_config WHERE id = 1")
        row = c.fetchone()

        conn.close()

        if row:
            return json.loads(row[0])

        from config.settings import PUSH_CFG

        return PUSH_CFG

    except Exception as e:
        log(f"获取推送配置出错: {str(e)}")

        from config.settings import PUSH_CFG

        return PUSH_CFG

import json
import os
from config.settings import DATA_DIR
from werkzeug.security import generate_password_hash, check_password_hash

AUTH_FILE = os.path.join(DATA_DIR, "auth_cfg.json")
DEF_AUTH = {"req_pwd": True, "pwd_h": generate_password_hash("admin")}  # 初始密码


def load_auth():

    try:
        with open(AUTH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return DEF_AUTH.copy()


def save_auth(cfg):

    if "pwd" in cfg:
        cfg["pwd_h"] = generate_password_hash(cfg.pop("pwd"))

    with open(AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=4)


def verify_pwd(pwd):

    cfg = load_auth()
    return check_password_hash(cfg["pwd_h"], pwd)

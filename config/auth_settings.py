import json
import os
from config.settings import DATA_DIR
from werkzeug.security import generate_password_hash, check_password_hash

CFG_FILE = os.path.join(DATA_DIR, "auth_cfg.json")
DEF_CFG = {"req_pwd": True, "pwd_hash": generate_password_hash("admin")}  # 初始化密码


def load_auth_cfg():

    try:
        with open(CFG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return DEF_CFG.copy()


def save_auth_cfg(cfg):

    if "pwd" in cfg:
        cfg["pwd_hash"] = generate_password_hash(cfg.pop("pwd"))

    with open(CFG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=4)


def verify_password(password):

    cfg = load_auth_cfg()
    return check_password_hash(cfg["pwd_hash"], password)

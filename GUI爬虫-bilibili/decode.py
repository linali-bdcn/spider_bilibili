import os
import sqlite3
import json
from base64 import b64decode
from Cryptodome.Cipher import AES  # Mac/Linux
import win32crypt  # Windows

def get_edge_cookies(domain=".bilibili.com"):
    # 定位 Edge Cookies 数据库路径
    edge_data_dir = os.path.expanduser(
        r"~\AppData\Local\Microsoft\Edge\User Data\Default\Network\Cookies"
    )
    local_state_path = os.path.expanduser(
        r"~\AppData\Local\Microsoft\Edge\User Data\Local State"
    )

    if not os.path.exists(edge_data_dir):
        raise FileNotFoundError("Edge Cookies 数据库未找到，请确保 Edge 已关闭！")

    # 连接数据库并查询指定域名的 Cookie
    conn = sqlite3.connect(edge_data_dir)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, encrypted_value, host_key FROM cookies WHERE host_key LIKE ?",
        (f"%{domain}%",),
    )
    cookies = cursor.fetchall()
    conn.close()

    # 从 Local State 获取加密密钥
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state = json.load(f)
    encrypted_key = b64decode(local_state["os_crypt"]["encrypted_key"])[5:]  # 移除 'DPAPI' 前缀

    # 解密密钥（Windows 使用 DPAPI，Mac/Linux 使用系统密钥环）
    try:
        # Windows 解密
        decrypted_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    except:
        # Mac/Linux 解密（需适配系统）
        pass

    # 解密 Cookie 的 encrypted_value
    decrypted_cookies = []
    for name, encrypted_value, host_key in cookies:
        if not encrypted_value:
            continue
        try:
            # 初始化 AES 解密器
            iv = encrypted_value[3:15]  # 提取初始化向量
            payload = encrypted_value[15:]  # 提取加密数据
            cipher = AES.new(decrypted_key, AES.MODE_GCM, iv)
            decrypted_value = cipher.decrypt(payload)[:-16].decode("utf-8")  # 移除尾部认证标签
            decrypted_cookies.append({"name": name, "value": decrypted_value, "domain": host_key})
        except Exception as e:
            print(f"解密失败: {name} - {e}")

    return decrypted_cookies

# 使用示例
cookies = get_edge_cookies(".bilibili.com")
for cookie in cookies:
    print(f"{cookie['name']}: {cookie['value']}")
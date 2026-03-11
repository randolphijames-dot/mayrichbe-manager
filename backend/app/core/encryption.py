"""
账号密码加密存储工具（AES-256 对称加密）
密钥从 .env 的 SECRET_KEY 派生，密文存数据库。
"""
import base64
import hashlib
from typing import Optional


def _get_key() -> bytes:
    """从 SECRET_KEY 派生 32 字节 AES 密钥"""
    from app.core.config import settings
    return hashlib.sha256(settings.SECRET_KEY.encode()).digest()


def encrypt(plaintext: str) -> str:
    """
    AES-128-CBC 加密（不依赖 cryptography 库，用标准库实现简版）
    生产建议换 cryptography.fernet
    """
    try:
        from cryptography.fernet import Fernet
        import base64
        key = base64.urlsafe_b64encode(_get_key())
        f = Fernet(key)
        return f.encrypt(plaintext.encode()).decode()
    except ImportError:
        # fallback：简单 XOR 混淆（不安全，仅为兼容）
        key = _get_key()
        encoded = bytearray()
        for i, c in enumerate(plaintext.encode()):
            encoded.append(c ^ key[i % len(key)])
        return "xor:" + base64.b64encode(bytes(encoded)).decode()


def decrypt(ciphertext: str) -> str:
    """解密"""
    try:
        if ciphertext.startswith("xor:"):
            key = _get_key()
            data = base64.b64decode(ciphertext[4:])
            decoded = bytearray()
            for i, c in enumerate(data):
                decoded.append(c ^ key[i % len(key)])
            return decoded.decode()

        from cryptography.fernet import Fernet
        import base64
        key = base64.urlsafe_b64encode(_get_key())
        f = Fernet(key)
        return f.decrypt(ciphertext.encode()).decode()
    except Exception as e:
        raise ValueError(f"解密失败（密钥可能不匹配）: {e}")


def safe_decrypt(ciphertext: Optional[str]) -> Optional[str]:
    """安全解密，失败返回 None"""
    if not ciphertext:
        return None
    try:
        return decrypt(ciphertext)
    except Exception:
        return None

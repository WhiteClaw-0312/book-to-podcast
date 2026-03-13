"""加密工具"""
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class Encryptor:
    """API Key 加密器"""
    
    def __init__(self, secret_key: str = None):
        """
        初始化加密器
        
        Args:
            secret_key: 加密密钥（从环境变量 SECRET_KEY 获取）
        """
        self.secret_key = secret_key or os.getenv("SECRET_KEY", "book-to-podcast-secret-key-2024")
        self._fernet = self._create_fernet()
    
    def _create_fernet(self) -> Fernet:
        """创建 Fernet 加密器"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'book-to-podcast-salt',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.secret_key.encode()))
        return Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """加密"""
        if not plaintext:
            return ""
        encrypted = self._fernet.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """解密"""
        if not ciphertext:
            return ""
        try:
            encrypted = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted = self._fernet.decrypt(encrypted)
            return decrypted.decode()
        except Exception:
            return ""


# 全局加密器实例
encryptor = Encryptor()


def encrypt_api_key(key: str) -> str:
    """加密 API Key"""
    return encryptor.encrypt(key)


def decrypt_api_key(encrypted_key: str) -> str:
    """解密 API Key"""
    return encryptor.decrypt(encrypted_key)
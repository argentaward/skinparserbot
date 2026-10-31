import base64
import hashlib
from typing import Optional
from cryptography.fernet import Fernet
from config import settings

_fernet_instance: Optional[Fernet] = None

def _get_fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is None:
        # Детерминированная генерация 32-байтового ключа из токена бота
        raw_key = hashlib.sha256(f"skinparser_secret_{settings.BOT_TOKEN}".encode()).digest()
        b64_key = base64.urlsafe_b64encode(raw_key)
        _fernet_instance = Fernet(b64_key)
    return _fernet_instance

def encrypt_key(plain_text: str) -> str:
    """
    Шифрует API-ключ в строку для безопасного хранения в БД.
    """
    if not plain_text:
        return ""
    fernet = _get_fernet()
    encrypted_bytes = fernet.encrypt(plain_text.strip().encode("utf-8"))
    return encrypted_bytes.decode("utf-8")

def decrypt_key(encrypted_text: Optional[str]) -> Optional[str]:
    """
    Расшифровывает API-ключ из БД.
    """
    if not encrypted_text:
        return None
    try:
        fernet = _get_fernet()
        decrypted_bytes = fernet.decrypt(encrypted_text.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except Exception:
        return None

def mask_api_key(api_key: Optional[str]) -> str:
    """
    Возвращает маскированный ключ для безопасного отображения пользователю (например: abcd...1234).
    """
    if not api_key:
        return "Не привязан"
    if len(api_key) <= 8:
        return "****"
    return f"{api_key[:4]}...{api_key[-4:]}"

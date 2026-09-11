import base64
import hashlib

from cryptography.fernet import Fernet


def _derive_key(encryption_key: str) -> bytes:
    digest = hashlib.sha256(encryption_key.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_token(token: str, encryption_key: str) -> str:
    f = Fernet(_derive_key(encryption_key))
    return f.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str, encryption_key: str) -> str:
    f = Fernet(_derive_key(encryption_key))
    return f.decrypt(encrypted_token.encode()).decode()


async def validate_canvas_token(canvas_url: str, token: str) -> dict:
    import httpx

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{canvas_url.rstrip('/')}/api/v1/users/self",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

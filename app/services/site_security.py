"""Private, persistent site security settings. Never return or log credentials."""
from datetime import datetime, timezone
import hmac
import json
import os
from pathlib import Path
import re
import stat
import tempfile

from fastapi import HTTPException


class DeletePasswordStore:
    def __init__(self, filename, legacy_password, *, hash_password, verify_password):
        self.path = Path(filename) if filename else None
        self.legacy_password = legacy_password
        self.hash_password = hash_password
        self.verify_password = verify_password

    def _read(self):
        if self.path is None:
            return None
        try:
            if not self.path.is_absolute() or self.path.is_symlink():
                raise ValueError("Unsafe settings path")
            try:
                info = self.path.stat()
            except FileNotFoundError:
                return None
            if not stat.S_ISREG(info.st_mode) or info.st_size > 4096:
                raise ValueError("Invalid settings file")
            if os.name == "posix" and stat.S_IMODE(info.st_mode) & 0o077:
                raise ValueError("Settings must be private")
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("version") != 1:
                raise ValueError("Invalid settings version")
            hashed = data.get("passwordHash")
            if not isinstance(hashed, str) or not re.fullmatch(r"pbkdf2_sha256\$260000\$[A-Za-z0-9_-]{16,64}\$[a-f0-9]{64}", hashed):
                raise ValueError("Invalid password hash")
            if not isinstance(data.get("updatedAt"), str) or len(data["updatedAt"]) > 40:
                raise ValueError("Invalid timestamp")
            return data
        except (OSError, ValueError, TypeError):
            raise HTTPException(503, "删除密码配置暂时不可用，请联系管理员。") from None

    def status(self):
        data = self._read()
        return {
            "usesServerPassword": data is None,
            "hasPassword": bool(data or self.legacy_password),
            "canChange": self.path is not None,
            "updatedAt": data["updatedAt"] if data else "",
            "minLength": 6,
            "maxLength": 128,
        }

    def verify(self, password):
        if not isinstance(password, str):
            return False
        data = self._read()
        if data:
            if len(password) > 128:
                return False
            return self.verify_password(password, data["passwordHash"])
        return bool(self.legacy_password) and hmac.compare_digest(password.encode("utf-8"), self.legacy_password.encode("utf-8"))

    @staticmethod
    def validate_new(password, confirmation):
        if not isinstance(password, str) or not isinstance(confirmation, str):
            raise HTTPException(400, "请输入有效的新删除密码及确认密码。")
        if not password and not confirmation:
            return False
        if len(password) < 6 or len(password) > 128:
            raise HTTPException(400, "新删除密码长度需为 6–128 位。")
        if password != password.strip() or any(ord(c) < 32 or ord(c) == 127 for c in password):
            raise HTTPException(400, "新删除密码不能包含首尾空格或控制字符。")
        if password != confirmation:
            raise HTTPException(400, "两次输入的新删除密码不一致。")
        return True

    def save(self, password, confirmation, *, actor_id):
        if not self.validate_new(password, confirmation):
            return False
        if self.path is None:
            raise HTTPException(503, "尚未配置删除密码的持久化存储，现有密码保持不变。")
        self._read()  # Refuse malformed, public, or symlinked configuration.
        data = {"version": 1, "passwordHash": self.hash_password(password),
                "updatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "updatedById": int(actor_id)}
        temp_path = None
        try:
            # Parent is provisioned by deployment outside all served media/static paths.
            if not self.path.parent.is_dir() or self.path.parent.is_symlink():
                raise OSError("Private settings directory unavailable")
            fd, name = tempfile.mkstemp(prefix=".site-security-", suffix=".tmp", dir=self.path.parent)
            temp_path = Path(name)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                if os.name == "posix":
                    os.fchmod(stream.fileno(), 0o600)
                json.dump(data, stream, ensure_ascii=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_path, self.path)
            temp_path = None
        except OSError:
            raise HTTPException(503, "删除密码保存失败，现有密码保持不变，请稍后重试。") from None
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink()
                except OSError:
                    pass
        return True

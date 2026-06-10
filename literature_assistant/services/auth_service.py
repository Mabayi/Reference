import bcrypt

from repositories import user_repo


def is_admin_user(user: dict | None) -> bool:
    """判断当前账号是否是系统管理员。"""
    return bool(user and user_repo.is_admin_username(user.get("username")))


def hash_password(plain: str) -> str:
    """使用 bcrypt 哈希密码。"""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """校验密码是否匹配。"""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_user(username: str, email: str, password: str) -> dict:
    """创建新用户。"""
    clean_username = username.strip()
    clean_email = email.strip()
    if not clean_username:
        raise ValueError("用户名不能为空")
    if not clean_email:
        raise ValueError("邮箱不能为空")
    if clean_username.lower() == "admin" and clean_username != "admin":
        raise ValueError("管理员账号用户名必须写为 admin")
    if user_repo.get_user_by_username(clean_username):
        raise ValueError("该用户名已被注册")
    if user_repo.get_user_by_email(clean_email):
        raise ValueError("该邮箱已被注册")
    if user_repo.get_user_by_email(clean_username):
        raise ValueError("用户名不能与已有邮箱相同")
    if user_repo.get_user_by_username(clean_email):
        raise ValueError("邮箱不能与已有用户名相同")
    password_hash = hash_password(password)
    return user_repo.create_user(clean_username, clean_email, password_hash)


def authenticate(identifier: str, password: str) -> dict | None:
    """用户登录认证。"""
    user = user_repo.get_user_by_identifier(identifier)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    user_repo.update_last_login(user["id"])
    return user

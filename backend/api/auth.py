"""
认证 API
用户登录、注册、Token 验证
"""
import re
import time
from collections import defaultdict, OrderedDict
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from jose import jwt
from sqlalchemy.orm import Session
import bcrypt

from database import get_db
from models.models import User
from config import settings
from api.deps import get_current_user

router = APIRouter()


# ==================== 登录速率限制 ====================
_login_attempts = defaultdict(list)  # {ip: [timestamp, ...]}
LOGIN_RATE_LIMIT = 5  # 每IP每分钟最多5次
LOGIN_RATE_WINDOW = 60  # 60秒窗口


def _check_login_rate(ip: str):
    """检查登录速率，超限则抛出429"""
    now = time.time()
    # 清理过期记录
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < LOGIN_RATE_WINDOW]
    if len(_login_attempts[ip]) >= LOGIN_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"登录尝试过于频繁，请{int(LOGIN_RATE_WINDOW - (now - _login_attempts[ip][0]))}秒后再试"
        )
    _login_attempts[ip].append(now)


# ==================== 注册速率限制（LRU，防止内存泄漏） ====================
class LRURateLimiter:
    """固定容量、自动清理的限流器"""
    def __init__(self, max_ips: int = 5000, max_attempts: int = 3, window: int = 300):
        self._data: OrderedDict[str, list] = OrderedDict()
        self.max_ips = max_ips
        self.max_attempts = max_attempts
        self.window = window

    def check(self, key: str):
        now = time.time()
        attempts = self._data.get(key, [])
        attempts = [t for t in attempts if now - t < self.window]

        if len(attempts) >= self.max_attempts:
            self._data[key] = attempts
            self._data.move_to_end(key)
            remaining = int(self.window - (now - attempts[0]))
            raise HTTPException(
                status_code=429,
                detail=f"操作过于频繁，请{remaining}秒后再试"
            )

        attempts.append(now)
        self._data[key] = attempts
        self._data.move_to_end(key)

        # 超容量时清理最早的条目
        if len(self._data) > self.max_ips:
            self._data.popitem(last=False)

_register_limiter = LRURateLimiter(max_ips=5000, max_attempts=3, window=300)


# ==================== 请求/响应模型 ====================
class LoginRequest(BaseModel):
    account: str   # 手机号或用户名
    password: str


class RegisterRequest(BaseModel):
    phone: str
    password: str
    real_name: str
    project_id: Optional[int] = None  # 前端辅助字段，不作为查找依据
    project_name: str  # ★ 必填：用户看到并选择的项目名称，唯一权威来源


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class UserInfo(BaseModel):
    id: int
    username: str
    phone: Optional[str] = None
    real_name: str
    role: str
    project_id: Optional[int] = None  # 保留兼容：默认/首个项目
    project_name: Optional[str] = None
    projects: list = []  # 关联的所有项目 [{id, name}, ...]

    class Config:
        from_attributes = True


# ==================== 工具函数 ====================
def get_user_projects_info(user, db):
    """获取用户关联的所有项目信息列表"""
    from models.models import UserProject, Project
    ups = db.query(UserProject).filter(UserProject.user_id == user.id).all()
    if ups:
        projects = []
        for up in ups:
            proj = db.query(Project).filter(Project.id == up.project_id).first()
            if proj:
                projects.append({"id": proj.id, "name": proj.name})
        return projects
    # 回退：从旧的 project_id 字段读取
    if user.project_id:
        proj = db.query(Project).filter(Project.id == user.project_id).first()
        if proj:
            return [{"id": proj.id, "name": proj.name}]
    return []


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def create_access_token(data: dict, expires_delta: timedelta = None):
    """创建 JWT Token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


# ==================== API 端点 ====================
@router.post("/login", response_model=TokenResponse, summary="用户登录")
async def login(request: Request, login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    用户登录
    - 支持手机号或用户名登录
    - 验证密码，返回 JWT Token
    - 速率限制：每IP每分钟5次
    """
    # 速率限制检查（优先使用 X-Real-IP，支持 Nginx 反向代理）
    client_ip = request.headers.get("x-real-ip") or request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "unknown")
    _check_login_rate(client_ip)
    # 查找用户：先按手机号查，再按用户名查
    account = login_data.account.strip()
    user = db.query(User).filter(User.phone == account).first()
    if not user:
        user = db.query(User).filter(User.username == account).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 验证密码
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 检查用户状态
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已被禁用"
        )

    # 创建 Token（包含 user_id 防止用户名冲突）
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "user_id": user.id}
    )

    # 审计日志
    from core.audit import log_action
    log_action("login", user_id=user.id, username=user.username,
                ip_address=request.headers.get("x-real-ip") or request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else None))

    # 获取用户关联的项目列表
    projects = get_user_projects_info(user, db)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        user={
            "id": user.id,
            "username": user.username,
            "phone": user.phone,
            "real_name": user.real_name,
            "role": user.role,
            "must_change_pwd": user.must_change_pwd,
            "project_id": user.project_id,
            "project_name": user.project.name if user.project else None,
            "projects": projects
        }
    )


@router.post("/register", summary="用户注册")
async def register(request: Request, data: RegisterRequest, db: Session = Depends(get_db)):
    """
    用户自注册（仅项目人员）
    - 使用手机号 + 密码 + 姓名注册
    - 默认角色为 project_staff（项目人员）
    - 用户名自动生成
    - 速率限制：每IP每5分钟3次
    """
    # 速率限制检查（优先使用 X-Real-IP，支持 Nginx 反向代理）
    client_ip = request.headers.get("x-real-ip") or request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "unknown")
    _register_limiter.check(f"register:{client_ip}")

    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"[注册] 收到请求: phone={data.phone}, project_id={data.project_id}, project_name={data.project_name}")

    phone = data.phone.strip()
    real_name = data.real_name.strip()

    # 校验手机号格式
    if not re.match(r'^1[3-9]\d{9}$', phone):
        raise HTTPException(status_code=400, detail="手机号格式不正确")

    # 校验密码强度（8位以上，包含字母和数字）
    pwd = data.password
    if len(pwd) < 8:
        raise HTTPException(status_code=400, detail="密码长度不能少于8位")
    if not re.search(r'[a-zA-Z]', pwd) or not re.search(r'\d', pwd):
        raise HTTPException(status_code=400, detail="密码需包含字母和数字")

    # 校验姓名
    if not real_name:
        raise HTTPException(status_code=400, detail="请填写真实姓名")

    # 检查手机号是否已注册
    existing = db.query(User).filter(User.phone == phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="该手机号已注册，请直接登录")

    # ★ 项目归属：project_name 是唯一权威来源（用户看到并选择的就是这个名字）
    from models.models import Project
    project = db.query(Project).filter(Project.name == data.project_name).first()
    if not project:
        raise HTTPException(status_code=400, detail=f"项目「{data.project_name}」不存在，请刷新页面后重试")
    logger.warning(f"[注册] 按project_name='{data.project_name}'查找项目: id={project.id}, name={project.name}")
    final_project_id = project.id

    # 生成用户名：u_手机号后4位_随机3位
    import random
    suffix = random.randint(100, 999)
    username = f"u_{phone[-4:]}_{suffix}"

    # 确保用户名唯一
    while db.query(User).filter(User.username == username).first():
        suffix = random.randint(100, 999)
        username = f"u_{phone[-4:]}_{suffix}"

    # 创建用户
    password_hash = bcrypt.hashpw(data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    logger.warning(f"[注册] 创建用户: username={username}, project_id={final_project_id}, project_name={project.name}")
    user = User(
        username=username,
        phone=phone,
        password_hash=password_hash,
        real_name=real_name,
        role="project_staff",
        project_id=final_project_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # ★★★ 关键修复：使用 raw SQL 直接读取数据库，绕过 ORM session 缓存
    # 之前的 ORM 验证 (db.query) 从 session identity map 返回对象，永远检测不到真实的数据库值
    from sqlalchemy import text as sql_text
    actual_row = db.execute(sql_text("SELECT project_id FROM users WHERE id = :uid"), {"uid": user.id}).fetchone()
    actual_db_project_id = actual_row[0] if actual_row else None

    logger.warning(f"[注册] Raw SQL 验证: user.id={user.id}, 期望project_id={final_project_id}, 数据库实际值={actual_db_project_id}")

    if actual_db_project_id != final_project_id:
        logger.error(f"[注册] ★★★ project_id 不一致！ORM={user.project_id}, DB实际={actual_db_project_id}, 期望={final_project_id}")
        # 使用 raw SQL 强制修正，不经过 ORM
        db.execute(sql_text("UPDATE users SET project_id = :pid WHERE id = :uid"), {"pid": final_project_id, "uid": user.id})
        db.commit()
        logger.warning(f"[注册] ★ 已通过 raw SQL 修正 project_id 为 {final_project_id}")

    # 写入 user_projects 多对多表
    from models.models import UserProject
    existing_up = db.query(UserProject).filter(
        UserProject.user_id == user.id, UserProject.project_id == final_project_id
    ).first()
    if not existing_up:
        db.add(UserProject(user_id=user.id, project_id=final_project_id))
        db.commit()

    # 自动登录：返回 Token
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "user_id": user.id}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        user={
            "id": user.id,
            "username": user.username,
            "phone": user.phone,
            "real_name": user.real_name,
            "role": user.role,
            "project_id": final_project_id,
            "project_name": project.name,
            "projects": [{"id": project.id, "name": project.name}]
        }
    )


class ChangePwdRequest(BaseModel):
    new_password: str


@router.post("/change-password", summary="修改密码")
async def change_password(
    request: ChangePwdRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """修改密码（首次登录强制改密）"""
    pwd = request.new_password
    if len(pwd) < 8:
        raise HTTPException(status_code=400, detail="密码长度不能少于8位")
    if not re.search(r'[a-zA-Z]', pwd) or not re.search(r'\d', pwd):
        raise HTTPException(status_code=400, detail="密码需包含字母和数字")

    current_user.password_hash = bcrypt.hashpw(
        request.new_password.encode('utf-8'), bcrypt.gensalt()
    ).decode('utf-8')
    current_user.must_change_pwd = False
    db.commit()

    return {"message": "密码修改成功"}


@router.get("/me", response_model=UserInfo, summary="获取当前用户信息")
async def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    获取当前登录用户信息
    """
    # 重新查询以获取最新的 project 关系
    user = db.query(User).filter(User.id == current_user.id).first()
    projects = get_user_projects_info(user, db)
    return UserInfo(
        id=user.id,
        username=user.username,
        phone=user.phone,
        real_name=user.real_name,
        role=user.role,
        project_id=user.project_id,
        project_name=user.project.name if user.project else None,
        projects=projects
    )


class AssignProjectsRequest(BaseModel):
    user_id: int
    project_ids: list[int]  # 要绑定的项目ID列表


@router.post("/assign-projects", summary="分配用户关联项目（管理员）")
async def assign_projects(
    data: AssignProjectsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """管理员给用户分配多个项目"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")

    from models.models import UserProject, Project
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 删除旧关联
    db.query(UserProject).filter(UserProject.user_id == data.user_id).delete()

    # 写入新关联
    for pid in data.project_ids:
        proj = db.query(Project).filter(Project.id == pid).first()
        if proj:
            db.add(UserProject(user_id=data.user_id, project_id=pid))

    # 更新默认 project_id 为第一个项目
    if data.project_ids:
        user.project_id = data.project_ids[0]

    db.commit()

    projects = get_user_projects_info(user, db)
    return {"success": True, "user_id": data.user_id, "projects": projects}


@router.get("/inspectors", summary="获取检查员列表")
async def get_inspectors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取所有检查员/阵地督导/驻场经理列表（用于任务分配）"""
    inspectors = db.query(User).filter(
        User.role.in_(["inspector", "site_supervisor", "field_supervisor"]),
        User.is_active == True
    ).all()

    return {
        "total": len(inspectors),
        "items": [
            {
                "id": u.id,
                "username": u.username,
                "real_name": u.real_name,
                "role": u.role
            }
            for u in inspectors
        ]
    }

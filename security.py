from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta


SECRET_KEY = "cb75315263c58c3ad8e460f3d105067356624ec6a524ab96b37663af30234829"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 3

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):              # ← add this
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
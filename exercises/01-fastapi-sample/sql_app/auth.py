from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"

api_key_header = APIKeyHeader(name="X-API-TOKEN")

def create_token(data: dict):
    encoded_jwt = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def verify_token(x_api_token: str = Depends(api_key_header)):
    payload = decode_token(x_api_token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    email = payload.get("sub")
    if email is None:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    return payload
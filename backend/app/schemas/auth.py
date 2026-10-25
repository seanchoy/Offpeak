from pydantic import BaseModel, EmailStr


class UserLogin(BaseModel):
    email: EmailStr
    password: str

class MobileLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    display_name: str
    accessibility: bool

class WebLoginResponse(BaseModel):
    message: str
    display_name: str
    accessibility: bool

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class WebRefreshResponse(BaseModel):
    message: str

class MobileRefreshResponse(BaseModel):
    access_token: str
    refresh_token: str

    model_config = {"from_attributes": True}

class LogoutRequest(BaseModel):
    refresh_token: str

class LogoutResponse(BaseModel):
    message: str

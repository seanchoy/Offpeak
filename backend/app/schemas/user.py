from pydantic import BaseModel, EmailStr, field_validator, model_validator
from pydantic_core import PydanticCustomError


class UserBase(BaseModel):
    email: EmailStr
    display_name: str
    accessibility: bool

class UserCreate(UserBase):
    password: str
    confirm_password: str

    @field_validator("password")
    @classmethod
    def password_length(cls, value):
        if len(value) < 6:
            raise PydanticCustomError(
                "password_too_short", 
                "Password must be at least 6 characters long."
            )
        elif len(value) > 128:
            raise PydanticCustomError(
                "password_too_long", 
                "Password must be at most 128 characters long."
            )
        return value

    @model_validator(mode="after")
    def check_passwords(self):
        if self.password != self.confirm_password:
            raise PydanticCustomError(
                "passwords_not_matching", 
                "Passwords do not match"
            )
        return self

    @field_validator("display_name")
    @classmethod
    def empty_display_name(cls, value):
        if not value.strip():
            raise PydanticCustomError(
                "empty_display_name", 
                "Display name cannot be blank."
            )
        return value

class UserResponse(UserBase):
    model_config = {"from_attributes": True}

class MeResponse(BaseModel):
    email: str
    display_name: str
    accessibility: bool

class UpdateMeRequest(BaseModel):
    display_name: str
    accessibility: bool

    @field_validator("display_name")
    @classmethod
    def clean_display_name(cls, value):
        value = value.strip()

        if not value:
            raise PydanticCustomError(
                "empty_display_name",
                "Display name cannot be blank."
            )

        if len(value) > 50:
            raise PydanticCustomError(
                "display_name_too_long",
                "Display name must be at most 50 characters."
            )

        return value

from fastapi import APIRouter
from app.models.Users.signUpSchema import UserSignUpSchema
from app.models.NGO.signUpSchema import NgoSignUpSchema
from app.models.logInSchema import loginSchema
from app.models.token import Token
from app.services.auth.Users.userSignUp import signup_user
from app.services.auth.NGO.NgoSignUp import signup_ngo
from app.services.auth.LogIn import login_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup/user")
async def register_user(data: UserSignUpSchema):
    return await signup_user(data)


@router.post("/signup/ngo")
async def register_ngo(data: NgoSignUpSchema):
    return await signup_ngo(data)


@router.post("/login", response_model=Token)
async def login(data: loginSchema):
    return await login_user(data)
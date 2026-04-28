from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal
from models.Users.signUpSchema import UserSignUpSchema
from models.NGO.signUpSchema import NgoSignUpSchema
from models.NGO.memberSignUpSchema import NgoMemberSignUpSchema
from models.Staff.signUpSchema import StaffSignUpSchema
from models.Volunteer.signUpSchema import VolunteerSignUpSchema
from models.logInSchema import loginSchema
from Validation.forgotPasswordValidation import ForgotPasswordValidationSchema
from Validation.resetPasswordValidation import ResetPasswordValidationSchema
from models.token import Token
from services.auth.Users.userSignUp import signup_user
from services.auth.NGO.NgoSignUp import signup_ngo
from services.auth.Staff.StaffSignUp import signup_staff
from services.auth.Volunteer.VolunteerSignUp import signup_volunteer
from services.auth.LogIn import login_user
from services.auth.ForgotPassword import forgot_password
from services.auth.ResetPassword import (
    reset_password,
    validate_reset_password_token,
)
from services.auth.user_id import generate_next_ngo_member_id

router = APIRouter(prefix="/auth", tags=["Auth"])


class GenerateRoleIdSchema(BaseModel):
    ngo_id: str
    identity_type: Literal["staff", "volunteer"]


@router.post("/signup/user")
async def register_user(data: UserSignUpSchema):
    return await signup_user(data)


@router.post("/signup/ngo")
async def register_ngo(data: NgoSignUpSchema):
    return await signup_ngo(data)


@router.post("/signup/staff")
async def register_staff(data: StaffSignUpSchema):
    return await signup_staff(data)


@router.post("/signup/volunteer")
async def register_volunteer(data: VolunteerSignUpSchema):
    return await signup_volunteer(data)


@router.post("/signup/ngo-member")
async def register_ngo_member(data: NgoMemberSignUpSchema):
    if data.identity_type == "staff":
        staff_payload = StaffSignUpSchema(
            name=data.name,
            email=data.email,
            password=data.password,
            ngo_id=data.ngo_id,
            designation=data.designation,
            contact_number=data.contact_number,
            user_id=data.role_id,
        )
        return await signup_staff(staff_payload)

    if not data.skill:
        raise HTTPException(status_code=400, detail="skill is required for volunteer signup")

    volunteer_payload = VolunteerSignUpSchema(
        name=data.name,
        email=data.email,
        password=data.password,
        ngo_id=data.ngo_id,
        skill=data.skill,
        contact_number=data.contact_number,
        location=data.location,
        user_id=data.role_id,
    )
    return await signup_volunteer(volunteer_payload)


@router.post("/signup/ngo-member/generate-role-id")
async def generate_ngo_member_role_id(data: GenerateRoleIdSchema):
    try:
        role_id = await generate_next_ngo_member_id(data.ngo_id, data.identity_type)
        return {
            "role_id": role_id,
            "identity_type": data.identity_type,
            "ngo_id": data.ngo_id,
        }
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.post("/login", response_model=Token)
async def login(data: loginSchema):
    return await login_user(data)


@router.post("/forgot-password")
async def forgot_password_controller(data: ForgotPasswordValidationSchema):
    return await forgot_password(data)


@router.post("/reset-password")
async def reset_password_controller(data: ResetPasswordValidationSchema):
    return await reset_password(data)


@router.get("/reset-password/validate")
async def validate_reset_password_token_controller(token: str):
    return await validate_reset_password_token(token)

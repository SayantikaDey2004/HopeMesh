from models.signOutSchema import SignOutSchema

class SignOutValidationController:
    @staticmethod
    def validate_signout():
        # No input needed for signout, just return schema
        return SignOutSchema()

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AgentPipelineError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class LinkedInAuthError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=401)


class LinkedInPublishError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=502)


class ImageGenerationError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=502)


class DraftNotFoundError(AppError):
    def __init__(self, draft_id: int):
        super().__init__(f"Draft {draft_id} not found", status_code=404)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message},
    )

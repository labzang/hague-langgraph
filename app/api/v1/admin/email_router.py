from fastapi import APIRouter
from app.domain.admin.models.email_model import EmailRequest

email_router = APIRouter(prefix="/email", tags=["mail"])

@email_router.post("/")
async def send_mail(email: EmailRequest):
    pass

@email_router.post("/")
async def spam_mail_filter(email: EmailRequest):
    pass

from aiogram import Router

from .balance import router as balance_router
from .chat import router as chat_router
from .cv import router as cv_router
from .fallback import router as fallback_router
from .generate import router as generate_router
from .job import router as job_router
from .jobs import router as jobs_router
from .resume import router as resume_router
from .resumes import router as resumes_router
from .start import router as start_router
from .topup import router as topup_router

router = Router(name=__name__)
router.include_router(start_router)
router.include_router(balance_router)
router.include_router(topup_router)
router.include_router(job_router)
router.include_router(jobs_router)
router.include_router(resumes_router)
router.include_router(resume_router)
router.include_router(cv_router)
router.include_router(generate_router)
router.include_router(chat_router)
router.include_router(fallback_router)

__all__ = ["router"]

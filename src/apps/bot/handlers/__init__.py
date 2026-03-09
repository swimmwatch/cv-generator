from aiogram import Router

from .cv import router as cv_router
from .fallback import router as fallback_router
from .job import router as job_router
from .jobs import router as jobs_router
from .start import router as start_router

router = Router(name=__name__)
router.include_router(start_router)
router.include_router(job_router)
router.include_router(jobs_router)
router.include_router(cv_router)
router.include_router(fallback_router)

__all__ = ["router"]

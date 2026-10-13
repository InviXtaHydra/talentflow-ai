from fastapi import APIRouter

from app.api.deps import CandidateUser, DbSession
from app.schemas.candidate import CandidateProfileOut, CandidateProfileUpdate, PreferencesIn, PreferencesOut
from app.schemas.common import Message
from app.services import candidate_service, dashboard_service
from app.services.matching import service as matching

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("/me", response_model=CandidateProfileOut)
def get_me(db: DbSession, user: CandidateUser) -> CandidateProfileOut:
    return candidate_service.profile_out(user, candidate_service.get_profile(db, user.id))


@router.patch("/me", response_model=CandidateProfileOut)
def update_me(body: CandidateProfileUpdate, db: DbSession, user: CandidateUser) -> CandidateProfileOut:
    return candidate_service.profile_out(user, candidate_service.update_profile(db, user, body))


@router.get("/me/preferences", response_model=PreferencesOut)
def get_preferences(db: DbSession, user: CandidateUser) -> PreferencesOut:
    return PreferencesOut.model_validate(candidate_service.get_preferences(db, user.id))


@router.put("/me/preferences", response_model=PreferencesOut)
def put_preferences(body: PreferencesIn, db: DbSession, user: CandidateUser) -> PreferencesOut:
    return PreferencesOut.model_validate(candidate_service.update_preferences(db, user, body))


@router.get("/me/dashboard")
def dashboard(db: DbSession, user: CandidateUser) -> dict:
    return dashboard_service.candidate_dashboard(db, user)


@router.post("/me/matches/recalculate", response_model=Message, summary="Recalculate all match scores for the current candidate")
def recalculate(db: DbSession, user: CandidateUser) -> Message:
    count = matching.recalculate_all(db, user)
    return Message(message=f"{count} matches herberekend.")

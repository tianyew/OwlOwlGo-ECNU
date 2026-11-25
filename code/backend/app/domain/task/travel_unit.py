"""Compatibility access to the pilot unit; the catalog is the sole source."""

from app.domain.content.catalog import get_quiz
from app.domain.content.catalog import grade as grade_quiz
from app.domain.content.catalog import public_questions as quiz_questions

UNIT_TITLE = "礼貌问路与方位"
QUESTIONS = get_quiz("unit-travel-0")["questions"]


def public_questions():
    return quiz_questions("unit-travel-0")


def grade(answers):
    return grade_quiz("unit-travel-0", answers)

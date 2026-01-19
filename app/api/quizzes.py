"""
Quiz generation and submission API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
import logging
from app.database import get_db
from app.models import Chapter, Quiz, QuizAttempt
from app.schemas.quiz import (
    QuizGenerateRequest,
    QuizResponse,
    QuizSubmission,
    QuizGradingResponse,
    QuestionGrading,
)
from app.services.gemini_service import gemini_service
from app.services.grading_service import grading_service
from app.utils.cache import cache_service    


router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])
logger = logging.getLogger(__name__)


@router.post("/generate/{chapter_id}", response_model=QuizResponse, status_code=201)
async def generate_quiz(
    chapter_id: UUID, request: QuizGenerateRequest, db: Session = Depends(get_db)
):
    """
    Generate a quiz for a chapter using Gemini AI

    - Checks cache first (1-hour TTL)
    - Uses Gemini File API for context-aware questions
    - Generates MCQs, short answers, and numerical problems
    - Stores quiz in database
    """

    # Verify chapter exists
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Generate cache key and variant hash
    cache_key = cache_service.generate_cache_key(
        str(chapter_id),
        request.difficulty,
        request.num_mcq,
        request.num_short,
        request.num_numerical,
    )

    variant_hash = cache_service.generate_variant_hash(
        str(chapter_id),
        request.difficulty,
        request.num_mcq,
        request.num_short,
        request.num_numerical,
    )

    # Check cache first
    cached_quiz = cache_service.get(cache_key)
    if cached_quiz:
        logger.info(f"Returning cached quiz for {cache_key}")
        return QuizResponse(**cached_quiz)

    # Check database for existing quiz with same variant
    existing_quiz = db.query(Quiz).filter(Quiz.variant_hash == variant_hash).first()

    if existing_quiz:
        logger.info(f"Found existing quiz in database: {existing_quiz.id}")
        response_data = {
            "quiz_id": existing_quiz.id,
            "questions": existing_quiz.questions,
            "total_questions": len(existing_quiz.questions),
            "total_points": sum(q.get("points", 1.0) for q in existing_quiz.questions),
        }

        # Cache it
        cache_service.set(cache_key, response_data)

        return QuizResponse(**response_data)

    try:
        # Generate new quiz using Gemini
        logger.info(f"Generating new quiz for chapter {chapter_id}")

        questions = gemini_service.generate_quiz(
            gemini_file_id=chapter.gemini_file_id,
            chapter_title=chapter.title,
            topics=chapter.topics or [],
            difficulty=request.difficulty,
            num_mcq=request.num_mcq,
            num_short=request.num_short,
            num_numerical=request.num_numerical,
        )

        # Calculate total points
        total_points = sum(q.get("points", 1.0) for q in questions)

        # Create quiz record
        quiz = Quiz(
            chapter_id=chapter_id,
            difficulty=request.difficulty,
            questions=questions,
            variant_hash=variant_hash,
        )

        db.add(quiz)
        db.commit()
        db.refresh(quiz)

        logger.info(f"Quiz created: {quiz.id}")

        # Prepare response
        response_data = {
            "quiz_id": quiz.id,
            "questions": questions,
            "total_questions": len(questions),
            "total_points": total_points,
        }

        # Cache the response
        cache_service.set(cache_key, response_data)

        return QuizResponse(**response_data)

    except Exception as e:
        logger.error(f"Failed to generate quiz: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to generate quiz: {str(e)}"
        )


@router.post("/{quiz_id}/submit", response_model=QuizGradingResponse)
async def submit_quiz(
    quiz_id: UUID, submission: QuizSubmission, db: Session = Depends(get_db)
):
    """
    Submit and grade a quiz

    Grading strategy:
    - MCQ: Exact match
    - Short Answer: Gemini semantic grading
    - Numerical: Tolerance (±2%) + Gemini fallback

    Returns:
    - Total score and breakdown
    - Weak topics identification
    - Personalized feedback
    """

    # Verify quiz exists
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Get chapter for context
    chapter = db.query(Chapter).filter(Chapter.id == quiz.chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    try:
        # Grade the quiz
        logger.info(f"Grading quiz {quiz_id} for user {submission.user_id}")

        total_score, breakdown, weak_topics, feedback = (
            await grading_service.grade_quiz(
                questions=quiz.questions,
                answers=submission.answers,
                gemini_file_id=chapter.gemini_file_id,
            )
        )

        # Calculate max score
        max_score = sum(q.get("points", 1.0) for q in quiz.questions)
        percentage = (total_score / max_score * 100) if max_score > 0 else 0.0

        # Store quiz attempt
        attempt = QuizAttempt(
            user_id=submission.user_id,
            quiz_id=quiz_id,
            answers=submission.answers,
            scores=breakdown,
            total_score=total_score,
            weak_topics=weak_topics,
        )

        db.add(attempt)
        db.commit()

        logger.info(
            f"Quiz attempt saved: {attempt.id}, score: {total_score}/{max_score}"
        )

        # Format breakdown for response
        formatted_breakdown = [QuestionGrading(**item) for item in breakdown]

        # Create score display in "X/Y" format (as per assignment)
        score_display = f"{total_score:.1f}/{max_score:.1f}"

        return QuizGradingResponse(
            score=round(total_score, 2),
            max_score=round(max_score, 2),
            score_display=score_display,
            percentage=round(percentage, 2),
            breakdown=formatted_breakdown,
            weak_topics=weak_topics,
            feedback=feedback,
        )

    except Exception as e:
        logger.error(f"Failed to grade quiz: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to grade quiz: {str(e)}")

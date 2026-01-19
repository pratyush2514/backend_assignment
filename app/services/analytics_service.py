"""
Analytics service for user and chapter performance tracking
"""
import logging
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from uuid import UUID
from collections import defaultdict
from app.models import Chapter, UserProgress, Quiz, QuizAttempt

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for generating performance analytics"""
    
    def get_user_performance(self, db: Session, user_id: UUID) -> Dict[str, Any]:
        """
        Get comprehensive performance analytics for a user
        
        Args:
            db: Database session
            user_id: User UUID
            
        Returns:
            Dictionary with performance metrics
        """
        
        # Get all user progress records
        progress_records = db.query(UserProgress).filter(
            UserProgress.user_id == user_id
        ).all()
        
        # Get all quiz attempts
        attempts = db.query(QuizAttempt).filter(
            QuizAttempt.user_id == user_id
        ).all()
        
        # Calculate overall metrics
        total_chapters = len(progress_records)
        completed_chapters = sum(1 for p in progress_records if p.is_completed)
        total_quiz_attempts = len(attempts)
        
        # Calculate average score
        if attempts:
            total_score = sum(float(a.total_score) for a in attempts if a.total_score)
            avg_score = total_score / len(attempts) if attempts else 0.0
        else:
            avg_score = 0.0
        
        # Topic mastery analysis
        topic_mastery = self._calculate_topic_mastery(db, attempts)
        
        # Chapter progress details
        chapter_progress = self._get_chapter_progress_details(db, progress_records, user_id)
        
        # Weak areas
        weak_areas = self._identify_weak_areas(attempts, topic_mastery)
        
        # Recommendations
        recommendations = self._generate_recommendations(
            completed_chapters, total_chapters, weak_areas, avg_score
        )
        
        return {
            "user_id": str(user_id),
            "total_chapters": total_chapters,
            "completed_chapters": completed_chapters,
            "total_quiz_attempts": total_quiz_attempts,
            "overall_avg_score": round(avg_score, 2),
            "topic_mastery": topic_mastery,
            "chapter_progress": chapter_progress,
            "weak_areas": weak_areas,
            "recommendations": recommendations
        }
    
    def _calculate_topic_mastery(
        self,
        db: Session,
        attempts: List[QuizAttempt]
    ) -> List[Dict[str, Any]]:
        """Calculate mastery level per topic"""
        
        topic_scores = defaultdict(list)
        
        for attempt in attempts:
            if attempt.scores:
                # scores is JSONB containing breakdown
                breakdown = attempt.scores if isinstance(attempt.scores, list) else []
                
                for item in breakdown:
                    if isinstance(item, dict):
                        topic = item.get("topic", "general")
                        score = item.get("score", 0)
                        max_score = item.get("max_score", 1)
                        
                        if max_score > 0:
                            topic_scores[topic].append(score / max_score)
        
        # Calculate mastery percentage per topic
        mastery_list = []
        for topic, scores in topic_scores.items():
            avg_score = sum(scores) / len(scores) if scores else 0.0
            mastery_list.append({
                "topic": topic,
                "mastery_percentage": round(avg_score * 100, 2),
                "attempts": len(scores),
                "avg_score": round(avg_score, 2)
            })
        
        # Sort by mastery descending
        mastery_list.sort(key=lambda x: x["mastery_percentage"], reverse=True)
        
        return mastery_list
    
    def _get_chapter_progress_details(
        self,
        db: Session,
        progress_records: List[UserProgress],
        user_id: UUID
    ) -> List[Dict[str, Any]]:
        """Get detailed progress for each chapter"""
        
        chapter_details = []
        
        for progress in progress_records:
            # Get chapter info
            chapter = db.query(Chapter).filter(Chapter.id == progress.chapter_id).first()
            
            if not chapter:
                continue
            
            # Get quiz attempts for this chapter
            quiz_ids = db.query(Quiz.id).filter(Quiz.chapter_id == progress.chapter_id).all()
            quiz_ids = [q_id[0] for q_id in quiz_ids]
            
            chapter_attempts = db.query(QuizAttempt).filter(
                and_(
                    QuizAttempt.user_id == user_id,
                    QuizAttempt.quiz_id.in_(quiz_ids)
                )
            ).all() if quiz_ids else []
            
            # Calculate average quiz score
            if chapter_attempts:
                avg_quiz_score = sum(float(a.total_score) for a in chapter_attempts if a.total_score) / len(chapter_attempts)
            else:
                avg_quiz_score = 0.0
            
            chapter_details.append({
                "chapter_id": str(chapter.id),
                "chapter_title": chapter.title,
                "completion_percentage": float(progress.scroll_progress) if progress.scroll_progress else 0.0,
                "is_completed": progress.is_completed,
                "time_spent": progress.time_spent or 0,
                "quiz_attempts": len(chapter_attempts),
                "avg_quiz_score": round(avg_quiz_score, 2)
            })
        
        return chapter_details
    
    def _identify_weak_areas(
        self,
        attempts: List[QuizAttempt],
        topic_mastery: List[Dict[str, Any]]
    ) -> List[str]:
        """Identify weak areas from quiz attempts"""
        
        weak_areas = set()
        
        # From quiz attempts
        for attempt in attempts:
            if attempt.weak_topics:
                weak_topics = attempt.weak_topics if isinstance(attempt.weak_topics, list) else []
                weak_areas.update(weak_topics)
        
        # From topic mastery (< 60%)
        for topic in topic_mastery:
            if topic["mastery_percentage"] < 60:
                weak_areas.add(topic["topic"])
        
        return sorted(list(weak_areas))
    
    def _generate_recommendations(
        self,
        completed: int,
        total: int,
        weak_areas: List[str],
        avg_score: float
    ) -> List[str]:
        """Generate personalized recommendations"""
        
        recommendations = []
        
        # Completion recommendations
        if total > 0:
            completion_rate = completed / total
            if completion_rate < 0.5:
                recommendations.append("Focus on completing more chapters to build a stronger foundation")
        
        # Performance recommendations
        if avg_score < 0.6:
            recommendations.append("Review fundamental concepts before attempting quizzes")
        elif avg_score < 0.8:
            recommendations.append("Practice more numerical problems to improve accuracy")
        else:
            recommendations.append("Excellent performance! Try harder difficulty levels")
        
        # Topic-specific recommendations
        if weak_areas:
            recommendations.append(f"Strengthen understanding in: {', '.join(weak_areas[:3])}")
        
        # General recommendation
        if not recommendations:
            recommendations.append("Keep up the good work! Continue regular practice")
        
        return recommendations
    
    def get_chapter_analytics(self, db: Session, chapter_id: UUID) -> Dict[str, Any]:
        """
        Get analytics for a specific chapter
        
        Args:
            db: Database session
            chapter_id: Chapter UUID
            
        Returns:
            Dictionary with chapter analytics
        """
        
        # Get chapter
        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter:
            return None
        
        # Get all progress records for this chapter
        progress_records = db.query(UserProgress).filter(
            UserProgress.chapter_id == chapter_id
        ).all()
        
        # Get all quizzes for this chapter
        quizzes = db.query(Quiz).filter(Quiz.chapter_id == chapter_id).all()
        quiz_ids = [q.id for q in quizzes]
        
        # Get all quiz attempts
        attempts = db.query(QuizAttempt).filter(
            QuizAttempt.quiz_id.in_(quiz_ids)
        ).all() if quiz_ids else []
        
        # Calculate metrics
        total_attempts = len(attempts)
        unique_users = len(set(str(a.user_id) for a in attempts))
        
        if attempts:
            avg_score = sum(float(a.total_score) for a in attempts if a.total_score) / len(attempts)
        else:
            avg_score = 0.0
        
        # Average completion time
        completed_progress = [p for p in progress_records if p.is_completed]
        if completed_progress:
            avg_completion_time = sum(p.time_spent for p in completed_progress if p.time_spent) / len(completed_progress)
        else:
            avg_completion_time = 0
        
        # Completion rate
        if progress_records:
            completion_rate = len(completed_progress) / len(progress_records)
        else:
            completion_rate = 0.0
        
        # Difficult questions
        difficult_questions = self._identify_difficult_questions(attempts, quizzes)
        
        # Common weak topics
        common_weak_topics = self._identify_common_weak_topics(attempts)
        
        return {
            "chapter_id": str(chapter_id),
            "chapter_title": chapter.title,
            "total_attempts": total_attempts,
            "unique_users": unique_users,
            "avg_score": round(avg_score, 2),
            "avg_completion_time": int(avg_completion_time),
            "difficult_questions": difficult_questions,
            "common_weak_topics": common_weak_topics,
            "completion_rate": round(completion_rate * 100, 2)
        }
    
    def _identify_difficult_questions(
        self,
        attempts: List[QuizAttempt],
        quizzes: List[Quiz]
    ) -> List[Dict[str, Any]]:
        """Identify questions with low average scores"""
        
        question_scores = defaultdict(lambda: {"scores": [], "topic": "", "text": ""})
        
        # Collect scores for each question
        for attempt in attempts:
            if attempt.scores:
                breakdown = attempt.scores if isinstance(attempt.scores, list) else []
                
                for item in breakdown:
                    if isinstance(item, dict):
                        q_id = item.get("q_id")
                        score = item.get("score", 0)
                        max_score = item.get("max_score", 1)
                        topic = item.get("topic", "general")
                        
                        if max_score > 0:
                            question_scores[q_id]["scores"].append(score / max_score)
                            question_scores[q_id]["topic"] = topic
        
        # Calculate averages and identify difficult ones
        difficult = []
        for q_id, data in question_scores.items():
            if len(data["scores"]) > 0:
                avg = sum(data["scores"]) / len(data["scores"])
                
                if avg < 0.5:  # Less than 50% average
                    # Find question text from quiz
                    question_text = "Question details not available"
                    for quiz in quizzes:
                        if quiz.questions:
                            questions = quiz.questions if isinstance(quiz.questions, list) else []
                            for q in questions:
                                if isinstance(q, dict) and q.get("q_id") == q_id:
                                    question_text = q.get("question", question_text)
                                    break
                    
                    difficult.append({
                        "q_id": q_id,
                        "question_text": question_text[:100] + "..." if len(question_text) > 100 else question_text,
                        "topic": data["topic"],
                        "attempts": len(data["scores"]),
                        "avg_score": round(avg, 2),
                        "common_mistakes": ["Review fundamental concepts", "Practice similar problems"]
                    })
        
        # Sort by difficulty (lowest avg first)
        difficult.sort(key=lambda x: x["avg_score"])
        
        return difficult[:5]  # Top 5 most difficult
    
    def _identify_common_weak_topics(self, attempts: List[QuizAttempt]) -> List[Dict[str, Any]]:
        """Identify most common weak topics across all attempts"""
        
        topic_weakness_count = defaultdict(int)
        topic_total_mentions = defaultdict(int)
        
        for attempt in attempts:
            # Count weak topics
            if attempt.weak_topics:
                weak = attempt.weak_topics if isinstance(attempt.weak_topics, list) else []
                for topic in weak:
                    topic_weakness_count[topic] += 1
            
            # Count all topic mentions
            if attempt.scores:
                breakdown = attempt.scores if isinstance(attempt.scores, list) else []
                for item in breakdown:
                    if isinstance(item, dict):
                        topic = item.get("topic", "general")
                        topic_total_mentions[topic] += 1
        
        # Calculate weakness percentage
        common_weak = []
        for topic, weak_count in topic_weakness_count.items():
            total = topic_total_mentions.get(topic, weak_count)
            weakness_pct = (weak_count / total * 100) if total > 0 else 0
            
            common_weak.append({
                "topic": topic,
                "weakness_count": weak_count,
                "weakness_percentage": round(weakness_pct, 2)
            })
        
        # Sort by weakness percentage
        common_weak.sort(key=lambda x: x["weakness_percentage"], reverse=True)
        
        return common_weak[:5]  # Top 5


# Global instance
analytics_service = AnalyticsService()
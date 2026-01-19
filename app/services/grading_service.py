"""
Quiz grading service with hybrid approach
MCQ: Exact match
Short/Numerical: Semantic grading via Gemini
"""
import logging
from typing import Dict, Any, List, Tuple
from app.services.gemini_service import gemini_service
from collections import Counter

logger = logging.getLogger(__name__)


class GradingService:
    """
    Service for grading quiz submissions
    
    Strategy:
    - MCQ: Exact match (deterministic, fast)
    - Short Answer: Gemini semantic grading (context-aware)
    - Numerical: Tolerance matching + Gemini fallback
    """
    
    NUMERICAL_TOLERANCE = 0.02  # ±2%
    
    async def grade_quiz(
        self,
        questions: List[Dict[str, Any]],
        answers: Dict[str, Any],
        gemini_file_id: str
    ) -> Tuple[float, List[Dict[str, Any]], List[str], str]:
        """
        Grade a complete quiz submission
        
        Args:
            questions: List of question dictionaries
            answers: User's answers {q_id: answer}
            gemini_file_id: Reference to chapter PDF
            
        Returns:
            Tuple of (total_score, breakdown, weak_topics, feedback)
        """
        
        breakdown = []
        total_score = 0.0
        max_score = 0.0
        topic_performance = {}  # {topic: [scores]}
        
        for question in questions:
            q_id = question["q_id"]
            q_type = question["type"]
            topic = question.get("topic", "general")
            points = question.get("points", 1.0)
            
            # Get user's answer
            user_answer = answers.get(q_id)
            
            # Grade based on type
            if q_type == "mcq":
                score, feedback, is_correct = self._grade_mcq(question, user_answer)
            elif q_type == "short":
                score, feedback, is_correct = await self._grade_short_answer(
                    question, user_answer, gemini_file_id
                )
            elif q_type == "numerical":
                score, feedback, is_correct = await self._grade_numerical(
                    question, user_answer, gemini_file_id
                )
            else:
                score, feedback, is_correct = 0.0, "Unknown question type", False
            
            # Calculate weighted score
            weighted_score = score * points
            total_score += weighted_score
            max_score += points
            
            # Track topic performance
            if topic not in topic_performance:
                topic_performance[topic] = []
            topic_performance[topic].append(score)
            
            # Add to breakdown
            breakdown.append({
                "q_id": q_id,
                "user_answer": user_answer,
                "correct_answer": question.get("correct_answer"),
                "score": weighted_score,
                "max_score": points,
                "feedback": feedback,
                "is_correct": is_correct,
                "topic": topic
            })
        
        # Identify weak topics (avg score < 0.6)
        weak_topics = [
            topic for topic, scores in topic_performance.items()
            if sum(scores) / len(scores) < 0.6
        ]
        
        # Generate overall feedback
        feedback = self._generate_feedback(total_score, max_score, weak_topics, breakdown)
        
        logger.info(f"Quiz graded: {total_score:.2f}/{max_score:.2f}, weak topics: {weak_topics}")
        
        return total_score, breakdown, weak_topics, feedback
    
    def _grade_mcq(
        self,
        question: Dict[str, Any],
        user_answer: Any
    ) -> Tuple[float, str, bool]:
        """
        Grade MCQ with exact match
        
        Args:
            question: Question dictionary
            user_answer: User's answer (index or letter)
            
        Returns:
            Tuple of (score, feedback, is_correct)
        """
        correct_answer = question.get("correct_answer")
        
        # Handle different answer formats
        if isinstance(user_answer, str) and user_answer.upper() in ['A', 'B', 'C', 'D']:
            # Convert letter to index
            user_answer = ord(user_answer.upper()) - ord('A')
        
        # Exact match
        if user_answer == correct_answer:
            return 1.0, "Correct!", True
        else:
            options = question.get("options", [])
            correct_text = options[correct_answer] if 0 <= correct_answer < len(options) else "Unknown"
            return 0.0, f"Incorrect. Correct answer: {correct_text}", False
    
    async def _grade_short_answer(
        self,
        question: Dict[str, Any],
        user_answer: str,
        gemini_file_id: str
    ) -> Tuple[float, str, bool]:
        """
        Grade short answer using Gemini semantic grading
        
        Args:
            question: Question dictionary
            user_answer: User's text answer
            gemini_file_id: Chapter PDF reference
            
        Returns:
            Tuple of (score, feedback, is_correct)
        """
        if not user_answer or not user_answer.strip():
            return 0.0, "No answer provided", False
        
        try:
            score, feedback = gemini_service.grade_answer(
                gemini_file_id=gemini_file_id,
                question=question["question"],
                correct_answer=question.get("correct_answer", ""),
                user_answer=user_answer,
                question_type="short",
                topic=question.get("topic", "general")
            )
            
            is_correct = score >= 0.7
            
            return score, feedback, is_correct
            
        except Exception as e:
            logger.error(f"Semantic grading failed: {str(e)}")
            # Fallback to keyword matching
            return self._fallback_keyword_grading(question, user_answer)
    
    async def _grade_numerical(
        self,
        question: Dict[str, Any],
        user_answer: Any,
        gemini_file_id: str
    ) -> Tuple[float, str, bool]:
        """
        Grade numerical answer with tolerance
        
        Args:
            question: Question dictionary
            user_answer: User's numerical answer
            gemini_file_id: Chapter PDF reference
            
        Returns:
            Tuple of (score, feedback, is_correct)
        """
        if user_answer is None or str(user_answer).strip() == "":
            return 0.0, "No answer provided", False
        
        try:
            # Parse correct answer
            correct_answer = float(question.get("correct_answer", 0))
            user_answer_float = float(user_answer)
            
            # Calculate tolerance range
            tolerance = abs(correct_answer * self.NUMERICAL_TOLERANCE)
            lower_bound = correct_answer - tolerance
            upper_bound = correct_answer + tolerance
            
            # Check if within tolerance
            if lower_bound <= user_answer_float <= upper_bound:
                return 1.0, f"Correct! (Answer: {correct_answer})", True
            else:
                # Outside tolerance - use Gemini for alternative methods
                score, feedback = gemini_service.grade_answer(
                    gemini_file_id=gemini_file_id,
                    question=question["question"],
                    correct_answer=str(correct_answer),
                    user_answer=str(user_answer),
                    question_type="numerical",
                    topic=question.get("topic", "general")
                )
                
                is_correct = score >= 0.7
                return score, feedback, is_correct
                
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to parse numerical answer: {str(e)}")
            return 0.0, f"Invalid numerical format. Expected: {question.get('correct_answer')}", False
    
    def _fallback_keyword_grading(
        self,
        question: Dict[str, Any],
        user_answer: str
    ) -> Tuple[float, str, bool]:
        """
        Fallback keyword-based grading if Gemini fails
        """
        correct_answer = question.get("correct_answer", "").lower()
        user_answer_lower = user_answer.lower()
        
        # Extract keywords from correct answer
        keywords = set(word for word in correct_answer.split() if len(word) > 3)
        
        # Count matching keywords
        matches = sum(1 for keyword in keywords if keyword in user_answer_lower)
        
        if len(keywords) == 0:
            return 0.5, "Unable to grade automatically", False
        
        score = matches / len(keywords)
        
        if score >= 0.7:
            feedback = "Good answer covering key points"
            is_correct = True
        elif score >= 0.4:
            feedback = "Partial answer, missing some key concepts"
            is_correct = False
        else:
            feedback = "Answer missing most key concepts"
            is_correct = False
        
        return score, feedback, is_correct
    
    def _generate_feedback(
        self,
        total_score: float,
        max_score: float,
        weak_topics: List[str],
        breakdown: List[Dict[str, Any]]
    ) -> str:
        """Generate overall feedback message"""
        
        percentage = (total_score / max_score * 100) if max_score > 0 else 0
        
        feedback_parts = []
        
        # Performance summary
        if percentage >= 90:
            feedback_parts.append("Excellent work! Strong understanding across all topics.")
        elif percentage >= 75:
            feedback_parts.append("Good performance! You have a solid grasp of the material.")
        elif percentage >= 60:
            feedback_parts.append("Fair performance. Review the weak areas for improvement.")
        else:
            feedback_parts.append("Needs improvement. Focus on understanding core concepts.")
        
        # Weak topics
        if weak_topics:
            feedback_parts.append(f"Focus on: {', '.join(weak_topics)}.")
        
        # Specific recommendations
        incorrect_questions = [item for item in breakdown if not item["is_correct"]]
        if incorrect_questions:
            topics_to_review = list(set(item["topic"] for item in incorrect_questions))
            feedback_parts.append(f"Review topics: {', '.join(topics_to_review)}.")
        
        return " ".join(feedback_parts)


# Global instance
grading_service = GradingService()
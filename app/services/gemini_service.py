"""
Gemini AI service for PDF processing, quiz generation, and grading
"""
import google.generativeai as genai
from app.config import settings
import json
import logging
from typing import List, Dict, Any, Tuple
import hashlib

logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(api_key=settings.GEMINI_API_KEY)


class GeminiService:
    """Service for all Gemini AI operations"""
    
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-3-flash-preview')
        self.vision_model = genai.GenerativeModel('gemini-3-flash-preview')
    
    def upload_and_index_pdf(self, file_path: str, display_name: str) -> Tuple[str, List[str]]:
        """
        Upload PDF to Gemini File API and extract topics
        
        Args:
            file_path: Path to PDF file
            display_name: Display name for the file
            
        Returns:
            Tuple of (gemini_file_id, extracted_topics)
        """
        try:
            # Upload file to Gemini (synchronous in newer versions)
            uploaded_file = genai.upload_file(path=file_path, display_name=display_name)
            logger.info(f"Uploaded file to Gemini: {uploaded_file.name}")
            
            # Extract topics using Gemini Vision
            topics = self._extract_topics(uploaded_file)
            
            return uploaded_file.name, topics
            
        except Exception as e:
            logger.error(f"Failed to upload PDF to Gemini: {str(e)}")
            raise
    
    def _extract_topics(self, uploaded_file) -> List[str]:
        """Extract main topics from the PDF"""
        try:
            prompt = """
            Analyze this educational chapter PDF and extract the main topics covered.
            Return ONLY a JSON array of topic strings (5-10 topics maximum).
            Format: ["topic1", "topic2", "topic3"]
            
            Focus on key concepts, formulas, theorems, or main learning objectives.
            """
            
            response = self.vision_model.generate_content([uploaded_file, prompt])
            
            # Parse JSON response
            topics_text = response.text.strip()
            # Remove markdown code blocks if present
            if topics_text.startswith("```json"):
                topics_text = topics_text[7:-3].strip()
            elif topics_text.startswith("```"):
                topics_text = topics_text[3:-3].strip()
            
            topics = json.loads(topics_text)
            return topics if isinstance(topics, list) else []
            
        except Exception as e:
            logger.warning(f"Failed to extract topics: {str(e)}")
            return ["general_concepts"]
    
    def generate_quiz(
        self,
        gemini_file_id: str,
        chapter_title: str,
        topics: List[str],
        difficulty: str,
        num_mcq: int,
        num_short: int,
        num_numerical: int
    ) -> List[Dict[str, Any]]:
        """
        Generate quiz questions using Gemini with File API context
        
        Args:
            gemini_file_id: Gemini file reference
            chapter_title: Chapter title
            topics: List of topics
            difficulty: easy/medium/hard
            num_mcq: Number of MCQ questions
            num_short: Number of short answer questions
            num_numerical: Number of numerical problems
            
        Returns:
            List of question dictionaries
        """
        try:
            # Get the uploaded file
            uploaded_file = genai.get_file(gemini_file_id)
            
            # Create structured prompt
            prompt = self._create_quiz_prompt(
                chapter_title, topics, difficulty, num_mcq, num_short, num_numerical
            )
            
            # Generate quiz with file context
            response = self.model.generate_content([uploaded_file, prompt])
            
            # Parse response
            questions = self._parse_quiz_response(response.text, num_mcq, num_short, num_numerical)
            
            return questions
            
        except Exception as e:
            logger.error(f"Failed to generate quiz: {str(e)}")
            raise
    
    def _create_quiz_prompt(
        self,
        chapter_title: str,
        topics: List[str],
        difficulty: str,
        num_mcq: int,
        num_short: int,
        num_numerical: int
    ) -> str:
        """Create structured prompt for quiz generation"""
        
        return f"""
You are an expert educator creating a {difficulty} level quiz for the chapter "{chapter_title}".

Topics to cover: {', '.join(topics)}

Generate EXACTLY {num_mcq + num_short + num_numerical} questions in the following format:

**MCQ Questions ({num_mcq} questions):**
- Multiple choice with 4 options
- One correct answer
- Realistic distractors based on common misconceptions

**Short Answer Questions ({num_short} questions):**
- Require 2-3 sentence explanations
- Test conceptual understanding
- Include expected key points in the answer

**Numerical Problems ({num_numerical} questions):**
- Require calculations
- Based on chapter examples
- Include step-by-step solution approach

Return ONLY valid JSON in this exact format (no markdown, no preamble):

[
  {{
    "q_id": "q1",
    "type": "mcq",
    "question": "Question text here?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": 0,
    "topic": "topic_name",
    "points": 1.0
  }},
  {{
    "q_id": "q2",
    "type": "short",
    "question": "Explain...",
    "correct_answer": "Expected answer with key points: point1, point2, point3",
    "topic": "topic_name",
    "points": 2.0
  }},
  {{
    "q_id": "q3",
    "type": "numerical",
    "question": "Calculate...",
    "correct_answer": "42.5",
    "topic": "topic_name",
    "points": 3.0
  }}
]

Ensure questions are directly from chapter content and test real understanding.
"""
    
    def _parse_quiz_response(self, response_text: str, num_mcq: int, num_short: int, num_numerical: int) -> List[Dict[str, Any]]:
        """Parse Gemini's quiz response into structured format"""
        try:
            # Clean response
            cleaned = response_text.strip()
            
            # Remove markdown code blocks
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:-3].strip()
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:-3].strip()
            
            # Parse JSON
            questions = json.loads(cleaned)
            
            # Validate structure
            if not isinstance(questions, list):
                raise ValueError("Response is not a list of questions")
            
            # Ensure we have the right number of questions
            total_expected = num_mcq + num_short + num_numerical
            if len(questions) != total_expected:
                logger.warning(f"Expected {total_expected} questions, got {len(questions)}")
            
            return questions
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse quiz JSON: {str(e)}")
            logger.error(f"Response text: {response_text[:500]}")
            
            # Fallback: create basic questions
            return self._create_fallback_questions(num_mcq, num_short, num_numerical)
    
    def _create_fallback_questions(self, num_mcq: int, num_short: int, num_numerical: int) -> List[Dict[str, Any]]:
        """Create fallback questions if parsing fails"""
        questions = []
        
        for i in range(num_mcq):
            questions.append({
                "q_id": f"q{i+1}",
                "type": "mcq",
                "question": f"Sample MCQ question {i+1}",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_answer": 0,
                "topic": "general",
                "points": 1.0
            })
        
        for i in range(num_short):
            questions.append({
                "q_id": f"q{num_mcq + i + 1}",
                "type": "short",
                "question": f"Sample short answer question {i+1}",
                "correct_answer": "Sample answer",
                "topic": "general",
                "points": 2.0
            })
        
        for i in range(num_numerical):
            questions.append({
                "q_id": f"q{num_mcq + num_short + i + 1}",
                "type": "numerical",
                "question": f"Sample numerical problem {i+1}",
                "correct_answer": "0",
                "topic": "general",
                "points": 3.0
            })
        
        return questions
    
    def grade_answer(
        self,
        gemini_file_id: str,
        question: str,
        correct_answer: str,
        user_answer: str,
        question_type: str,
        topic: str
    ) -> Tuple[float, str]:
        """
        Grade a subjective answer using Gemini with chapter context
        
        Args:
            gemini_file_id: Reference to chapter PDF
            question: The question text
            correct_answer: Expected/reference answer
            user_answer: Student's answer
            question_type: short or numerical
            topic: Question topic
            
        Returns:
            Tuple of (score, feedback)
        """
        try:
            uploaded_file = genai.get_file(gemini_file_id)
            
            prompt = f"""
You are grading a student's answer for this question from the chapter.

**Question:** {question}
**Topic:** {topic}
**Expected Answer:** {correct_answer}
**Student's Answer:** {user_answer}

Grade the student's answer on a scale of 0.0 to 1.0 based on:
1. Correctness of key concepts
2. Completeness
3. Understanding demonstrated

For numerical answers, allow ±2% tolerance for rounding.

Return ONLY valid JSON (no markdown):
{{
  "score": 0.85,
  "feedback": "Good understanding of main concept. Missing minor detail about..."
}}
"""
            
            response = self.model.generate_content([uploaded_file, prompt])
            
            # Parse response
            result_text = response.text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:-3].strip()
            elif result_text.startswith("```"):
                result_text = result_text[3:-3].strip()
            
            result = json.loads(result_text)
            score = float(result.get("score", 0.0))
            feedback = result.get("feedback", "No feedback provided")
            
            # Clamp score between 0 and 1
            score = max(0.0, min(1.0, score))
            
            return score, feedback
            
        except Exception as e:
            logger.error(f"Failed to grade answer: {str(e)}")
            # Fallback to simple matching
            if user_answer.lower().strip() == correct_answer.lower().strip():
                return 1.0, "Correct answer"
            else:
                return 0.5, "Partial credit - please review the concept"


# Global instance
gemini_service = GeminiService()
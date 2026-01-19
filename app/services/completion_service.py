"""
Chapter completion detection service
Multi-factor algorithm for reliable completion tracking
"""
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class CompletionService:
    """
    Service for detecting chapter completion using multi-factor algorithm
    
    Algorithm: Weighted scoring across three dimensions
    - Time spent (30%): Expected 10 min per 10 pages = 600 seconds baseline
    - Scroll progress (40%): Direct percentage of content viewed
    - Interaction (30%): Text selections indicate engagement
    
    Threshold: 75% composite score = completed
    """
    
    # Weights for each factor (must sum to 1.0)
    WEIGHT_TIME = 0.30
    WEIGHT_SCROLL = 0.40
    WEIGHT_INTERACTION = 0.30
    
    # Completion threshold
    THRESHOLD = 0.75
    
    # Expected baseline: 10 minutes per 10 pages (600 seconds)
    EXPECTED_TIME_PER_PAGE = 60  # seconds
    BASELINE_PAGES = 10
    
    def calculate_completion(
        self,
        time_spent: int,
        scroll_pct: float,
        selections: int = 0,
        estimated_pages: int = 10
    ) -> Tuple[bool, float, str]:
        """
        Calculate chapter completion status
        
        Args:
            time_spent: Time in seconds
            scroll_pct: Scroll percentage (0-100)
            selections: Number of text selections
            estimated_pages: Estimated page count
            
        Returns:
            Tuple of (is_completed, completion_percentage, method_details)
        """
        
        # Calculate individual scores
        time_score = self._calculate_time_score(time_spent, estimated_pages)
        scroll_score = self._calculate_scroll_score(scroll_pct)
        interaction_score = self._calculate_interaction_score(selections, time_spent)
        
        # Weighted composite score
        composite_score = (
            time_score * self.WEIGHT_TIME +
            scroll_score * self.WEIGHT_SCROLL +
            interaction_score * self.WEIGHT_INTERACTION
        )
        
        # Determine completion
        is_completed = composite_score >= self.THRESHOLD
        
        # Method details for transparency
        method_details = (
            f"multi_factor_v1|time:{time_score:.2f}|"
            f"scroll:{scroll_score:.2f}|interact:{interaction_score:.2f}|"
            f"composite:{composite_score:.2f}"
        )
        
        logger.info(
            f"Completion calculation: time_spent={time_spent}s, "
            f"scroll={scroll_pct}%, selections={selections}, "
            f"composite={composite_score:.2f}, completed={is_completed}"
        )
        
        return is_completed, composite_score, method_details
    
    def _calculate_time_score(self, time_spent: int, estimated_pages: int) -> float:
        """
        Calculate time-based score
        
        Logic: 
        - Expected time = pages * 60 seconds
        - Score = min(time_spent / expected_time, 1.0)
        - Cap at 1.0 to prevent over-counting idle time
        """
        expected_time = estimated_pages * self.EXPECTED_TIME_PER_PAGE
        
        if expected_time == 0:
            expected_time = self.BASELINE_PAGES * self.EXPECTED_TIME_PER_PAGE
        
        score = min(time_spent / expected_time, 1.0)
        
        return score
    
    def _calculate_scroll_score(self, scroll_pct: float) -> float:
        """
        Calculate scroll-based score
        
        Logic:
        - Direct mapping: scroll_pct / 100
        - Most reliable single indicator
        """
        return min(scroll_pct / 100.0, 1.0)
    
    def _calculate_interaction_score(self, selections: int, time_spent: int) -> float:
        """
        Calculate interaction-based score
        
        Logic:
        - Expect ~1 selection per 2 minutes of reading
        - Score based on selection density
        - High selections + reasonable time = engaged learning
        """
        if time_spent == 0:
            return 0.0
        
        # Expected selections: 1 every 120 seconds
        expected_selections = max(time_spent / 120, 1)
        
        # Score based on ratio
        selection_ratio = selections / expected_selections
        
        # Cap at 1.0 (over-selecting doesn't mean more learning)
        score = min(selection_ratio, 1.0)
        
        return score
    
    def estimate_pages_from_pdf_size(self, file_size_bytes: int) -> int:
        """
        Estimate page count from PDF file size
        
        Rough heuristic: ~50KB per page for text-heavy PDFs
        """
        avg_bytes_per_page = 50 * 1024  # 50KB
        estimated_pages = max(file_size_bytes // avg_bytes_per_page, 5)
        
        # Cap between 5 and 50 pages (reasonable chapter length)
        return min(max(estimated_pages, 5), 50)


# Global instance
completion_service = CompletionService()
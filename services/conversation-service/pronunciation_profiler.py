"""
Pronunciation profiling system using Thompson Sampling bandits
and vector space modeling for language learning.
"""

import numpy as np
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import json

from phoneme_mappings import PhonemeMapper, LANGUAGE_PHONEMES


class BanditStrategy(Enum):
    CHALLENGE = "challenge"  # Focus on weak phonemes
    ENCOURAGE = "encourage"  # Practice strong phonemes


@dataclass
class PronunciationAttempt:
    """Single pronunciation attempt record."""
    timestamp: datetime
    phoneme: str
    accuracy: float
    context: str  # word/sentence containing the phoneme
    session_id: str


@dataclass
class PhonemeConfidence:
    """Confidence tracking for a single phoneme."""
    successes: int = 1  # Alpha parameter (starts with prior)
    failures: int = 1   # Beta parameter (starts with prior)
    attempts: int = 0
    last_updated: datetime = None
    
    @property
    def confidence_mean(self) -> float:
        """Beta distribution mean."""
        return self.successes / (self.successes + self.failures)
    
    @property
    def confidence_variance(self) -> float:
        """Beta distribution variance."""
        alpha, beta = self.successes, self.failures
        return (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1))
    
    def update(self, success: bool):
        """Update based on pronunciation attempt."""
        if success:
            self.successes += 1
        else:
            self.failures += 1
        self.attempts += 1
        self.last_updated = datetime.utcnow()


class ThompsonSamplingBandit:
    """Thompson Sampling bandit for phoneme selection."""
    
    def __init__(self, phonemes: List[str]):
        self.phonemes = phonemes
        self.confidences = {
            phoneme: PhonemeConfidence() for phoneme in phonemes
        }
    
    def sample_phoneme(self, exclude: Optional[List[str]] = None) -> str:
        """Sample phoneme based on Thompson Sampling."""
        available_phonemes = [
            p for p in self.phonemes 
            if not exclude or p not in exclude
        ]
        
        if not available_phonemes:
            available_phonemes = self.phonemes
        
        # Sample from Beta distributions
        samples = {}
        for phoneme in available_phonemes:
            conf = self.confidences[phoneme]
            # Sample from Beta(successes, failures)
            sample = np.random.beta(conf.successes, conf.failures)
            samples[phoneme] = sample
        
        # Return phoneme with highest/lowest sample based on strategy
        return max(samples.keys(), key=lambda p: samples[p])
    
    def update_phoneme(self, phoneme: str, success: bool):
        """Update phoneme confidence based on pronunciation result."""
        if phoneme in self.confidences:
            self.confidences[phoneme].update(success)
    
    def get_phoneme_ranking(self, ascending: bool = True) -> List[Tuple[str, float]]:
        """Get phonemes ranked by confidence."""
        rankings = [
            (phoneme, conf.confidence_mean) 
            for phoneme, conf in self.confidences.items()
        ]
        return sorted(rankings, key=lambda x: x[1], reverse=not ascending)


class PronunciationProfileManager:
    """Manages user pronunciation profiles with dual bandits."""
    
    def __init__(self, llm_service_url: str):
        self.llm_service_url = llm_service_url
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.phoneme_mapper = PhonemeMapper()
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()
    
    def create_profile(self, user_id: str, language: str) -> Dict[str, Any]:
        """Create new pronunciation profile for user."""
        phonemes = LANGUAGE_PHONEMES.get(language, [])
        
        profile = {
            "user_id": user_id,
            "language": language,
            "created_at": datetime.utcnow(),
            "last_updated": datetime.utcnow(),
            "weakness_bandit": ThompsonSamplingBandit(phonemes),
            "strength_bandit": ThompsonSamplingBandit(phonemes),
            "recent_attempts": [],
            "session_history": [],
            "metadata": {
                "total_attempts": 0,
                "overall_accuracy": 0.0,
                "last_compaction": datetime.utcnow()
            }
        }
        
        return profile
    
    async def get_bandit_strategy_from_llm(
        self, 
        user_profile: Dict[str, Any],
        conversation_context: str
    ) -> BanditStrategy:
        """Use LLM to determine optimal bandit strategy based on user mood/fatigue."""
        
        recent_attempts = user_profile.get("recent_attempts", [])
        recent_accuracy = self._calculate_recent_accuracy(recent_attempts)
        
        # Prepare context for LLM
        context_data = {
            "recent_accuracy": recent_accuracy,
            "attempt_count": len(recent_attempts),
            "conversation_snippet": conversation_context[-500:],  # Last 500 chars
            "session_duration_minutes": self._get_session_duration(user_profile),
            "overall_accuracy": user_profile["metadata"]["overall_accuracy"]
        }
        
        prompt = f"""
        Analyze this language learner's current state and decide the optimal pronunciation practice strategy:
        
        Context:
        - Recent accuracy: {context_data['recent_accuracy']:.1%}
        - Attempts in current session: {context_data['attempt_count']}
        - Session duration: {context_data['session_duration_minutes']} minutes
        - Overall accuracy: {context_data['overall_accuracy']:.1%}
        - Recent conversation: "{context_data['conversation_snippet']}"
        
        Choose strategy:
        A) CHALLENGE - Practice difficult sounds (when user is confident, energetic)
        B) ENCOURAGE - Practice familiar sounds (when user seems tired, frustrated)
        
        Consider: user mood, fatigue level, confidence, learning effectiveness
        
        Respond with just: "CHALLENGE" or "ENCOURAGE"
        """
        
        try:
            response = await self.http_client.post(
                f"{self.llm_service_url}/analyze-strategy",
                json={"prompt": prompt}
            )
            
            if response.status_code == 200:
                result = response.json()
                strategy_text = result.get("strategy", "ENCOURAGE").upper()
                return BanditStrategy.CHALLENGE if "CHALLENGE" in strategy_text else BanditStrategy.ENCOURAGE
            else:
                # Default to encourage if LLM call fails
                return BanditStrategy.ENCOURAGE
                
        except Exception as e:
            print(f"Error getting bandit strategy from LLM: {e}")
            # Fallback logic based on recent performance
            if recent_accuracy > 0.8 and len(recent_attempts) < 5:
                return BanditStrategy.CHALLENGE
            else:
                return BanditStrategy.ENCOURAGE
    
    async def suggest_target_phonemes(
        self, 
        user_profile: Dict[str, Any],
        conversation_context: str,
        count: int = 3
    ) -> List[str]:
        """Suggest phonemes for practice based on bandit strategy."""
        
        strategy = await self.get_bandit_strategy_from_llm(user_profile, conversation_context)
        
        if strategy == BanditStrategy.CHALLENGE:
            # Use weakness bandit - focus on difficult phonemes
            bandit = user_profile["weakness_bandit"]
            # Get phonemes with lowest confidence (most challenging)
            weak_phonemes = bandit.get_phoneme_ranking(ascending=True)
            return [phoneme for phoneme, _ in weak_phonemes[:count]]
        
        else:
            # Use strength bandit - practice familiar phonemes  
            bandit = user_profile["strength_bandit"]
            # Get phonemes with higher confidence (encouraging)
            strong_phonemes = bandit.get_phoneme_ranking(ascending=False)
            return [phoneme for phoneme, _ in strong_phonemes[:count]]
    
    def update_profile_with_evaluation(
        self, 
        user_profile: Dict[str, Any],
        character_errors: List[Dict[str, Any]],
        overall_accuracy: float,
        intended_text: str,
        actual_text: str,
        language: str
    ) -> Dict[str, Any]:
        """Update pronunciation profile based on evaluation results."""
        
        # Extract phonemes from intended text
        intended_phonemes = self.phoneme_mapper.extract_phonemes_from_text(intended_text, language)
        
        # Update bandits based on character errors
        weakness_bandit = user_profile["weakness_bandit"]
        strength_bandit = user_profile["strength_bandit"]
        
        # Process each character error
        for error in character_errors:
            if error["type"] in ["mispronounced_character", "missing_character"]:
                expected_char = error.get("expected", "")
                
                # Map character to phoneme
                phonemes_affected = self._map_character_to_phonemes(expected_char, language)
                
                for phoneme in phonemes_affected:
                    # Update weakness bandit (error = failure)
                    weakness_bandit.update_phoneme(phoneme, success=False)
                    # Also update strength bandit
                    strength_bandit.update_phoneme(phoneme, success=False)
        
        # Update successful phonemes
        successful_phonemes = intended_phonemes - set(self._extract_error_phonemes(character_errors, language))
        for phoneme in successful_phonemes:
            weakness_bandit.update_phoneme(phoneme, success=True)
            strength_bandit.update_phoneme(phoneme, success=True)
        
        # Record attempt
        attempt = PronunciationAttempt(
            timestamp=datetime.utcnow(),
            phoneme="mixed",  # Multiple phonemes in sentence
            accuracy=overall_accuracy / 100.0,
            context=intended_text,
            session_id=self._get_current_session_id(user_profile)
        )
        
        user_profile["recent_attempts"].append(asdict(attempt))
        
        # Keep only recent attempts (last 20)
        user_profile["recent_attempts"] = user_profile["recent_attempts"][-20:]
        
        # Update metadata
        user_profile["metadata"]["total_attempts"] += 1
        user_profile["metadata"]["overall_accuracy"] = self._calculate_overall_accuracy(user_profile)
        user_profile["last_updated"] = datetime.utcnow()
        
        return user_profile
    
    def _map_character_to_phonemes(self, character: str, language: str) -> List[str]:
        """Map a character to corresponding phonemes."""
        # For now, simple 1:1 mapping
        # In production, this could be more sophisticated
        if character in LANGUAGE_PHONEMES.get(language, []):
            return [character]
        return []
    
    def _extract_error_phonemes(self, character_errors: List[Dict[str, Any]], language: str) -> set:
        """Extract phonemes that had errors."""
        error_phonemes = set()
        for error in character_errors:
            if error["type"] in ["mispronounced_character", "missing_character"]:
                expected_char = error.get("expected", "")
                phonemes = self._map_character_to_phonemes(expected_char, language)
                error_phonemes.update(phonemes)
        return error_phonemes
    
    def _calculate_recent_accuracy(self, recent_attempts: List[Dict[str, Any]]) -> float:
        """Calculate accuracy from recent attempts."""
        if not recent_attempts:
            return 0.5  # Neutral default
        
        accuracies = [attempt["accuracy"] for attempt in recent_attempts[-10:]]
        return sum(accuracies) / len(accuracies)
    
    def _calculate_overall_accuracy(self, user_profile: Dict[str, Any]) -> float:
        """Calculate overall accuracy from all attempts."""
        all_attempts = user_profile.get("recent_attempts", []) + user_profile.get("session_history", [])
        if not all_attempts:
            return 0.5
        
        accuracies = [attempt["accuracy"] for attempt in all_attempts]
        return sum(accuracies) / len(accuracies)
    
    def _get_session_duration(self, user_profile: Dict[str, Any]) -> int:
        """Get current session duration in minutes."""
        recent_attempts = user_profile.get("recent_attempts", [])
        if not recent_attempts:
            return 0
        
        first_attempt = datetime.fromisoformat(recent_attempts[0]["timestamp"])
        duration = datetime.utcnow() - first_attempt
        return int(duration.total_seconds() / 60)
    
    def _get_current_session_id(self, user_profile: Dict[str, Any]) -> str:
        """Generate or get current session ID."""
        # Simple session ID based on date
        return datetime.utcnow().strftime("%Y%m%d-%H")
    
    async def should_compact_profile(self, user_profile: Dict[str, Any]) -> bool:
        """Determine if profile needs compaction."""
        last_compaction = user_profile["metadata"].get("last_compaction")
        if not last_compaction:
            return False
        
        # Compact if more than 7 days since last compaction
        time_since_compaction = datetime.utcnow() - last_compaction
        return time_since_compaction > timedelta(days=7)
    
    async def compact_profile_with_llm(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM to compact pronunciation profile by summarizing patterns."""
        
        # This would be implemented to summarize long-term patterns
        # and reduce the size of stored data while preserving insights
        
        # For now, simple approach: move old attempts to session_history
        if len(user_profile["recent_attempts"]) > 50:
            # Move older attempts to history
            old_attempts = user_profile["recent_attempts"][:-20]
            user_profile["session_history"].extend(old_attempts)
            user_profile["recent_attempts"] = user_profile["recent_attempts"][-20:]
            
            # Update compaction timestamp
            user_profile["metadata"]["last_compaction"] = datetime.utcnow()
        
        return user_profile
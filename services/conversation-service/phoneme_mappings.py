"""
Phoneme mappings for pronunciation profiling across supported languages.

This module defines the phonemic inventory for each language, providing
the foundation for vector space pronunciation modeling.
"""

from typing import Dict, List, Set

# Tamil Phonemes based on linguistic analysis
TAMIL_PHONEMES = {
    # Vowels (உயிர்)
    "vowels": [
        "அ", "ஆ", "இ", "ஈ", "உ", "ஊ", "எ", "ஏ", "ஐ", "ஒ", "ஓ", "ஔ"
    ],
    
    # Consonants (மெய்)
    "stops": [
        # Voiceless stops
        "க", "ச", "ட", "த", "ப", "ற",
        # Voiced/aspirated variants
        "ங", "ஞ", "ண", "ந", "ம", "ன"
    ],
    
    "liquids": ["ய", "ர", "ல", "வ", "ழ", "ள"],
    
    "fricatives": ["ஸ", "ஷ", "ஜ", "ஹ"],
    
    # Common phonemically distinct combinations
    "combinations": ["க்ஷ", "ஸ்ரீ", "க்ரி", "ப்ரி", "த்ரி"]
}

# Malayalam Phonemes
MALAYALAM_PHONEMES = {
    # Vowels
    "vowels": [
        "അ", "ആ", "ഇ", "ഈ", "ഉ", "ഊ", "എ", "ഏ", "ഐ", "ഒ", "ഓ", "ഔ"
    ],
    
    # Consonants
    "stops": [
        "ക", "ച", "ട", "ത", "പ", "റ",
        "ഗ", "ജ", "ഡ", "ദ", "ബ", "ഴ"
    ],
    
    "nasals": ["ങ", "ഞ", "ണ", "ന", "മ"],
    
    "liquids": ["യ", "ര", "ല", "വ", "ള"],
    
    "fricatives": ["ശ", "ഷ", "സ", "ഹ"],
    
    "combinations": ["ക്ഷ", "ശ്രീ", "ത്ര", "പ്ര", "ബ്ര"]
}

# English Phonemes (IPA-based for precision)
ENGLISH_PHONEMES = {
    # Vowels (monophthongs)
    "vowels": [
        "æ",  # cat
        "ɑ",  # father  
        "ɔ",  # caught
        "ɛ",  # bet
        "ɪ",  # bit
        "ʊ",  # book
        "ʌ",  # but
        "ə",  # about
        "i",  # beat
        "u",  # boot
        "eɪ", # bait
        "oʊ", # boat
        "aɪ", # bite
        "aʊ", # bout
        "ɔɪ"  # boy
    ],
    
    # Consonants
    "stops": ["p", "b", "t", "d", "k", "g"],
    "fricatives": ["f", "v", "θ", "ð", "s", "z", "ʃ", "ʒ", "h"],
    "affricates": ["tʃ", "dʒ"],
    "nasals": ["m", "n", "ŋ"],
    "liquids": ["l", "r"],
    "glides": ["w", "j"]
}

# Romanized mappings for cross-script analysis
TAMIL_ROMANIZED = {
    # Vowels
    "அ": "a", "ஆ": "aa", "இ": "i", "ஈ": "ii", "உ": "u", "ஊ": "uu",
    "எ": "e", "ஏ": "ee", "ஐ": "ai", "ஒ": "o", "ஓ": "oo", "ஔ": "au",
    
    # Consonants  
    "க": "ka", "ச": "cha", "ட": "ta", "த": "tha", "ப": "pa", "ற": "ra",
    "ங": "nga", "ஞ": "nya", "ண": "na", "ந": "nha", "ம": "ma", "ன": "na",
    "ய": "ya", "ர": "ra", "ல": "la", "வ": "va", "ழ": "zha", "ள": "lla",
    "ஸ": "sa", "ஷ": "sha", "ஜ": "ja", "ஹ": "ha"
}

MALAYALAM_ROMANIZED = {
    # Vowels
    "അ": "a", "ആ": "aa", "ഇ": "i", "ഈ": "ii", "ഉ": "u", "ഊ": "uu",
    "എ": "e", "ഏ": "ee", "ഐ": "ai", "ഒ": "o", "ഓ": "oo", "ഔ": "au",
    
    # Consonants
    "ക": "ka", "ച": "cha", "ട": "ta", "ത": "tha", "പ": "pa", "റ": "ra",
    "ഗ": "ga", "ജ": "ja", "ഡ": "da", "ദ": "dha", "ബ": "ba", "ഴ": "zha",
    "ങ": "nga", "ഞ": "nya", "ണ": "na", "ന": "na", "മ": "ma",
    "യ": "ya", "ര": "ra", "ല": "la", "വ": "va", "ള": "lla",
    "ശ": "sha", "ഷ": "sha", "സ": "sa", "ഹ": "ha"
}

# Complete language phoneme inventory
LANGUAGE_PHONEMES = {
    "English": (
        ENGLISH_PHONEMES["vowels"] + 
        ENGLISH_PHONEMES["stops"] + 
        ENGLISH_PHONEMES["fricatives"] + 
        ENGLISH_PHONEMES["affricates"] + 
        ENGLISH_PHONEMES["nasals"] + 
        ENGLISH_PHONEMES["liquids"] + 
        ENGLISH_PHONEMES["glides"]
    ),
    "Tamil": (
        TAMIL_PHONEMES["vowels"] + 
        TAMIL_PHONEMES["stops"] + 
        TAMIL_PHONEMES["liquids"] + 
        TAMIL_PHONEMES["fricatives"] + 
        TAMIL_PHONEMES["combinations"]
    ),
    "Malayalam": (
        MALAYALAM_PHONEMES["vowels"] + 
        MALAYALAM_PHONEMES["stops"] + 
        MALAYALAM_PHONEMES["nasals"] + 
        MALAYALAM_PHONEMES["liquids"] + 
        MALAYALAM_PHONEMES["fricatives"] + 
        MALAYALAM_PHONEMES["combinations"]
    )
}

# Reverse mappings for analysis
ROMANIZED_TO_PHONEME = {
    "Tamil": {v: k for k, v in TAMIL_ROMANIZED.items()},
    "Malayalam": {v: k for k, v in MALAYALAM_ROMANIZED.items()}
}

class PhonemeMapper:
    """Utility class for phoneme mapping and analysis."""
    
    @staticmethod
    def get_phonemes_for_language(language: str) -> List[str]:
        """Get complete phoneme inventory for a language."""
        return LANGUAGE_PHONEMES.get(language, [])
    
    @staticmethod
    def extract_phonemes_from_text(text: str, language: str) -> Set[str]:
        """Extract phonemes present in given text."""
        phonemes = set()
        
        if language == "English":
            # For English, we'd need a phonetic transcription library
            # For now, approximate with character analysis
            for char in text.lower():
                if char in LANGUAGE_PHONEMES["English"]:
                    phonemes.add(char)
        
        elif language in ["Tamil", "Malayalam"]:
            # Direct character-to-phoneme mapping
            for char in text:
                if char in LANGUAGE_PHONEMES[language]:
                    phonemes.add(char)
        
        return phonemes
    
    @staticmethod
    def map_romanized_to_phoneme(romanized_text: str, language: str) -> List[str]:
        """Convert romanized text back to phonemes."""
        if language not in ROMANIZED_TO_PHONEME:
            return []
        
        mapping = ROMANIZED_TO_PHONEME[language]
        phonemes = []
        
        # Simple greedy matching (can be improved with better algorithms)
        i = 0
        while i < len(romanized_text):
            found = False
            # Try longest matches first
            for length in range(min(4, len(romanized_text) - i), 0, -1):
                substr = romanized_text[i:i+length]
                if substr in mapping:
                    phonemes.append(mapping[substr])
                    i += length
                    found = True
                    break
            if not found:
                i += 1
        
        return phonemes
    
    @staticmethod
    def get_phoneme_similarity_groups(language: str) -> Dict[str, List[str]]:
        """Get groups of similar phonemes for confusion analysis."""
        similarity_groups = {
            "Tamil": {
                "ka_group": ["க", "ங"],
                "cha_group": ["ச", "ஞ"], 
                "ta_group": ["ட", "ண"],
                "tha_group": ["த", "ந"],
                "pa_group": ["ப", "ம"],
                "liquids": ["ய", "ர", "ல", "வ", "ழ", "ள"]
            },
            "Malayalam": {
                "ka_group": ["ക", "ഗ", "ങ"],
                "cha_group": ["ച", "ജ", "ഞ"],
                "ta_group": ["ട", "ഡ", "ണ"],
                "tha_group": ["ത", "ദ", "ന"],
                "pa_group": ["പ", "ബ", "മ"],
                "liquids": ["യ", "ര", "ല", "വ", "ള"]
            },
            "English": {
                "fricatives": ["f", "v", "θ", "ð", "s", "z", "ʃ", "ʒ"],
                "stops": ["p", "b", "t", "d", "k", "g"],
                "vowels_front": ["i", "ɪ", "eɪ", "ɛ", "æ"],
                "vowels_back": ["u", "ʊ", "oʊ", "ɔ", "ɑ"]
            }
        }
        
        return similarity_groups.get(language, {})
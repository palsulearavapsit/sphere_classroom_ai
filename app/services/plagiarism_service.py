"""
AI Plagiarism Detection Service
Provides comprehensive plagiarism checking using AI-powered similarity analysis
"""

import os
import json
import hashlib
from datetime import datetime
from flask import current_app
from ..ai.gemini_client import ask_gemini
from ..db import get_db

class PlagiarismDetectionService:
    def __init__(self):
        self.similarity_threshold = 0.7  # 70% similarity threshold
        self.min_chunk_size = 50  # Minimum characters for meaningful comparison
        
    def init_ai(self):
        """Initialize AI for plagiarism detection (uses gemini_client)"""
        try:
            # Test if ask_gemini is available
            from ..ai.gemini_client import ask_gemini
            print("[SUCCESS] Plagiarism Detection AI initialized successfully")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to initialize AI for plagiarism detection: {e}")
            return False
        
    def check_plagiarism(self, text, user_id=None, assignment_id=None, exclude_user_id=None):
        """
        Comprehensive plagiarism check combining multiple detection methods
        
        Args:
            text (str): Text to check for plagiarism
            user_id (int): ID of user submitting the text
            assignment_id (int): Assignment ID for context
            exclude_user_id (int): User ID to exclude from comparison (e.g., original author)
            
        Returns:
            dict: Comprehensive plagiarism report
        """
        if not text or len(text.strip()) < self.min_chunk_size:
            return {
                "overall_score": 0.0,
                "risk_level": "low",
                "matches": [],
                "ai_analysis": "Text too short for meaningful analysis",
                "recommendations": []
            }
        
        try:
            # 1. Database similarity check
            db_matches = self._check_database_similarity(text, user_id, assignment_id, exclude_user_id)
            
            # 2. AI-powered content analysis
            ai_analysis = self._ai_plagiarism_analysis(text)
            
            # 3. Pattern recognition
            pattern_matches = self._check_writing_patterns(text)
            
            # 4. Calculate overall plagiarism score
            overall_score = self._calculate_overall_score(db_matches, ai_analysis, pattern_matches)
            
            # 5. Generate recommendations
            recommendations = self._generate_recommendations(overall_score, db_matches, ai_analysis)
            
            # 6. Store check in database for future reference
            check_id = self._store_plagiarism_check(text, user_id, assignment_id, overall_score)
            
            return {
                "check_id": check_id,
                "overall_score": overall_score,
                "risk_level": self._get_risk_level(overall_score),
                "database_matches": db_matches,
                "ai_analysis": ai_analysis,
                "pattern_matches": pattern_matches,
                "recommendations": recommendations,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            current_app.logger.error(f"Plagiarism check error: {str(e)}")
            return {
                "overall_score": 0.0,
                "risk_level": "error",
                "error": str(e),
                "matches": [],
                "recommendations": ["Please try again or contact support"]
            }
    
    def _check_database_similarity(self, text, user_id, assignment_id, exclude_user_id):
        """Check similarity against existing submissions in database"""
        db = get_db()
        matches = []
        
        try:
            # Query existing submissions
            query = """
                SELECT id, user_id, content, created_at 
                FROM assessment_submissions 
                WHERE LENGTH(content) > ? 
            """
            params = [self.min_chunk_size]
            
            if assignment_id:
                query += " AND assessment_id = ?"
                params.append(assignment_id)
                
            if exclude_user_id:
                query += " AND user_id != ?"
                params.append(exclude_user_id)
                
            query += " ORDER BY created_at DESC LIMIT 100"
            
            submissions = db.execute(query, params).fetchall()
            
            # Calculate similarity with each submission
            for submission in submissions:
                similarity = self._calculate_text_similarity(text, submission['content'])
                
                if similarity > 0.3:  # Only report significant similarities
                    matches.append({
                        "submission_id": submission['id'],
                        "user_id": submission['user_id'],
                        "similarity_score": similarity,
                        "match_type": "database",
                        "created_at": submission['created_at'],
                        "severity": self._get_similarity_severity(similarity)
                    })
            
            # Sort by similarity score
            matches.sort(key=lambda x: x['similarity_score'], reverse=True)
            return matches[:10]  # Return top 10 matches
            
        except Exception as e:
            current_app.logger.error(f"Database similarity check error: {str(e)}")
            return []
    
    def _calculate_text_similarity(self, text1, text2):
        """Calculate similarity between two texts using multiple methods"""
        if not text1 or not text2:
            return 0.0
        
        # Normalize texts
        text1_clean = self._normalize_text(text1)
        text2_clean = self._normalize_text(text2)
        
        # Method 1: Jaccard similarity on words
        words1 = set(text1_clean.split())
        words2 = set(text2_clean.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        jaccard_similarity = len(intersection) / len(union)
        
        # Method 2: Sequence similarity for exact matches
        sequence_similarity = self._longest_common_subsequence_ratio(text1_clean, text2_clean)
        
        # Method 3: N-gram similarity
        ngram_similarity = self._ngram_similarity(text1_clean, text2_clean, n=3)
        
        # Weighted combination
        combined_similarity = (
            jaccard_similarity * 0.4 +
            sequence_similarity * 0.3 +
            ngram_similarity * 0.3
        )
        
        return min(combined_similarity, 1.0)
    
    def _normalize_text(self, text):
        """Normalize text for comparison"""
        import re
        # Convert to lowercase
        text = text.lower()
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove punctuation but keep word boundaries
        text = re.sub(r'[^\w\s]', '', text)
        return text.strip()
    
    def _longest_common_subsequence_ratio(self, text1, text2):
        """Calculate LCS ratio between two texts"""
        def lcs_length(s1, s2):
            m, n = len(s1), len(s2)
            dp = [[0] * (n + 1) for _ in range(m + 1)]
            
            for i in range(1, m + 1):
                for j in range(1, n + 1):
                    if s1[i-1] == s2[j-1]:
                        dp[i][j] = dp[i-1][j-1] + 1
                    else:
                        dp[i][j] = max(dp[i-1][j], dp[i][j-1])
            
            return dp[m][n]
        
        lcs_len = lcs_length(text1, text2)
        max_len = max(len(text1), len(text2))
        
        return lcs_len / max_len if max_len > 0 else 0.0
    
    def _ngram_similarity(self, text1, text2, n=3):
        """Calculate n-gram similarity between texts"""
        def get_ngrams(text, n):
            return set(text[i:i+n] for i in range(len(text) - n + 1))
        
        ngrams1 = get_ngrams(text1, n)
        ngrams2 = get_ngrams(text2, n)
        
        if not ngrams1 or not ngrams2:
            return 0.0
        
        intersection = ngrams1.intersection(ngrams2)
        union = ngrams1.union(ngrams2)
        
        return len(intersection) / len(union)
    
    def _ai_plagiarism_analysis(self, text):
        """Use AI to analyze text for potential plagiarism indicators"""
        try:
            prompt = f"""
Analyze the following text for potential plagiarism indicators. Look for:

1. Writing style inconsistencies
2. Sudden changes in vocabulary or complexity
3. Formatting inconsistencies
4. Suspicious phrases or academic jargon
5. Signs of copy-paste from multiple sources

Text to analyze:
{text}

Provide a JSON response with:
{{
    "style_consistency": "consistent|inconsistent",
    "vocabulary_analysis": "appropriate|suspicious",
    "formatting_issues": ["list of issues"],
    "suspicious_phrases": ["list of phrases"],
    "ai_confidence": 0.0-1.0,
    "analysis_summary": "brief summary",
    "red_flags": ["list of red flags"]
}}
"""
            
            response = ask_gemini(prompt)
            
            # Try to parse JSON response
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # Fallback to text analysis
                return {
                    "style_consistency": "unknown",
                    "vocabulary_analysis": "unknown", 
                    "formatting_issues": [],
                    "suspicious_phrases": [],
                    "ai_confidence": 0.5,
                    "analysis_summary": response[:200] + "..." if len(response) > 200 else response,
                    "red_flags": []
                }
                
        except Exception as e:
            current_app.logger.error(f"AI plagiarism analysis error: {str(e)}")
            return {
                "error": str(e),
                "ai_confidence": 0.0,
                "analysis_summary": "AI analysis unavailable"
            }
    
    def _check_writing_patterns(self, text):
        """Check for suspicious writing patterns"""
        patterns = []
        
        # Check for sudden style changes
        sentences = text.split('.')
        if len(sentences) > 3:
            # Analyze sentence length variation
            lengths = [len(s.strip()) for s in sentences if s.strip()]
            if lengths:
                avg_length = sum(lengths) / len(lengths)
                variations = [abs(l - avg_length) for l in lengths]
                high_variation = sum(1 for v in variations if v > avg_length * 0.5) / len(variations)
                
                if high_variation > 0.3:
                    patterns.append({
                        "type": "style_inconsistency",
                        "severity": "medium",
                        "description": "Inconsistent sentence length patterns detected"
                    })
        
        # Check for mixed citation styles
        citation_patterns = [
            r'\([A-Za-z]+,?\s*\d{4}\)',  # (Author, 2023)
            r'\[\d+\]',                   # [1]
            r'[A-Za-z]+\s*\(\d{4}\)',    # Author (2023)
        ]
        
        import re
        citation_types = []
        for pattern in citation_patterns:
            if re.search(pattern, text):
                citation_types.append(pattern)
        
        if len(citation_types) > 1:
            patterns.append({
                "type": "mixed_citations",
                "severity": "low",
                "description": "Multiple citation styles detected"
            })
        
        return patterns
    
    def _calculate_overall_score(self, db_matches, ai_analysis, pattern_matches):
        """Calculate overall plagiarism risk score"""
        score = 0.0
        
        # Database matches weight (40%)
        if db_matches:
            max_db_similarity = max(match['similarity_score'] for match in db_matches)
            score += max_db_similarity * 0.4
        
        # AI analysis weight (35%)
        if 'ai_confidence' in ai_analysis:
            ai_score = ai_analysis['ai_confidence']
            if ai_analysis.get('style_consistency') == 'inconsistent':
                ai_score += 0.2
            if ai_analysis.get('vocabulary_analysis') == 'suspicious':
                ai_score += 0.2
            score += min(ai_score, 1.0) * 0.35
        
        # Pattern analysis weight (25%)
        pattern_score = 0.0
        for pattern in pattern_matches:
            if pattern['severity'] == 'high':
                pattern_score += 0.3
            elif pattern['severity'] == 'medium':
                pattern_score += 0.2
            elif pattern['severity'] == 'low':
                pattern_score += 0.1
        
        score += min(pattern_score, 1.0) * 0.25
        
        return min(score, 1.0)
    
    def _get_risk_level(self, score):
        """Convert numeric score to risk level"""
        if score >= 0.8:
            return "very_high"
        elif score >= 0.6:
            return "high"
        elif score >= 0.4:
            return "medium"
        elif score >= 0.2:
            return "low"
        else:
            return "very_low"
    
    def _get_similarity_severity(self, similarity):
        """Convert similarity score to severity level"""
        if similarity >= 0.8:
            return "very_high"
        elif similarity >= 0.6:
            return "high"
        elif similarity >= 0.4:
            return "medium"
        else:
            return "low"
    
    def _generate_recommendations(self, score, db_matches, ai_analysis):
        """Generate actionable recommendations based on plagiarism analysis"""
        recommendations = []
        
        if score >= 0.8:
            recommendations.append("🚨 Very high plagiarism risk detected - manual review required")
            recommendations.append("Check for proper citations and quotations")
            recommendations.append("Verify originality of content")
        elif score >= 0.6:
            recommendations.append("⚠️ High similarity detected - review recommended")
            recommendations.append("Check citation formatting and attribution")
        elif score >= 0.4:
            recommendations.append("💡 Moderate similarity - consider reviewing sources")
            recommendations.append("Ensure proper paraphrasing and attribution")
        elif score >= 0.2:
            recommendations.append("✅ Low risk - minor similarities detected")
            recommendations.append("Good academic writing practices observed")
        else:
            recommendations.append("✅ Very low risk - content appears original")
        
        # Specific recommendations based on AI analysis
        if 'red_flags' in ai_analysis:
            for flag in ai_analysis['red_flags']:
                recommendations.append(f"🔍 Review: {flag}")
        
        # Database match recommendations
        if db_matches:
            high_matches = [m for m in db_matches if m['similarity_score'] > 0.7]
            if high_matches:
                recommendations.append(f"📋 Found {len(high_matches)} high-similarity matches in database")
        
        return recommendations
    
    def _store_plagiarism_check(self, text, user_id, assignment_id, score):
        """Store plagiarism check result in database"""
        db = get_db()
        
        try:
            # Create hash of text for future reference
            text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
            
            db.execute("""
                INSERT INTO plagiarism_checks 
                (user_id, assignment_id, text_hash, content_sample, plagiarism_score, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                assignment_id, 
                text_hash,
                text[:500],  # Store first 500 chars as sample
                score,
                datetime.utcnow().isoformat()
            ))
            db.commit()
            
            check_id = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
            return check_id
            
        except Exception as e:
            current_app.logger.error(f"Error storing plagiarism check: {str(e)}")
            return None
    
    def get_plagiarism_history(self, user_id, limit=20):
        """Get plagiarism check history for a user"""
        db = get_db()
        
        try:
            checks = db.execute("""
                SELECT id, assignment_id, content_sample, plagiarism_score, created_at
                FROM plagiarism_checks 
                WHERE user_id = ?
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, limit)).fetchall()
            
            return [dict(check) for check in checks]
            
        except Exception as e:
            current_app.logger.error(f"Error getting plagiarism history: {str(e)}")
            return []

# Global service instance
plagiarism_service = PlagiarismDetectionService()
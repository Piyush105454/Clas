"""
Student Growth Intelligence Service

Provides ML-based analysis for student growth tracking including:
- Attendance pattern analysis
- Quiz trend detection
- Text evolution analysis
- Feature engineering
- Student clustering
- Growth score calculation
- Insight generation
- At-risk detection
"""

import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from django.db.models import Q, Avg, Count, StdDev
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer

from ..models import (
    Enrollment, Attendance, SessionFeedback, StudentQuiz, 
    StudentGrowthAnalysis, AttendanceStatus, StudentFeedback
)

logger = logging.getLogger(__name__)


class AttendanceAnalyzer:
    """Analyzes attendance patterns and consistency"""
    
    MIN_SESSIONS = 5
    
    @staticmethod
    def analyze_pattern(enrollment: Enrollment) -> Dict:
        """
        Analyze attendance pattern for a student.
        
        Returns:
            Dict with pattern, consistency_score, trend, and insights
        """
        # Get attendance records
        attendances = Attendance.objects.filter(
            enrollment=enrollment
        ).order_by('marked_at').values_list('status', 'marked_at')
        
        if len(attendances) < AttendanceAnalyzer.MIN_SESSIONS:
            return {
                'pattern': 'insufficient_data',
                'consistency_score': 0,
                'trend': 'unknown',
                'data_points': len(attendances),
                'min_required': AttendanceAnalyzer.MIN_SESSIONS,
            }
        
        # Extract status values
        statuses = [att[0] for att in attendances]
        dates = [att[1] for att in attendances]
        
        # Calculate present count
        present_count = sum(1 for s in statuses if s == AttendanceStatus.PRESENT)
        total_count = len(statuses)
        attendance_percentage = (present_count / total_count) * 100
        
        # Calculate consistency (std dev of intervals between sessions)
        intervals = []
        for i in range(1, len(dates)):
            interval = (dates[i] - dates[i-1]).days
            if interval > 0:
                intervals.append(interval)
        
        if intervals:
            consistency_std = np.std(intervals)
            # Normalize to 0-100 (lower std = higher consistency)
            consistency_score = max(0, 100 - (consistency_std * 5))
        else:
            consistency_score = 100
        
        # Detect trend (recent vs older)
        mid_point = len(statuses) // 2
        recent_present = sum(1 for s in statuses[mid_point:] if s == AttendanceStatus.PRESENT)
        older_present = sum(1 for s in statuses[:mid_point] if s == AttendanceStatus.PRESENT)
        
        recent_rate = recent_present / len(statuses[mid_point:]) if len(statuses[mid_point:]) > 0 else 0
        older_rate = older_present / len(statuses[:mid_point]) if len(statuses[:mid_point]) > 0 else 0
        
        if recent_rate > older_rate + 0.1:
            trend = 'improving'
        elif recent_rate < older_rate - 0.1:
            trend = 'declining'
        else:
            trend = 'stable'
        
        # Classify pattern
        if consistency_score > 80 and attendance_percentage > 80:
            pattern = 'stable'
        elif trend == 'declining':
            pattern = 'declining'
        elif consistency_score < 50:
            pattern = 'irregular'
        elif trend == 'improving':
            pattern = 'improving'
        else:
            pattern = 'stable'
        
        return {
            'pattern': pattern,
            'consistency_score': consistency_score,
            'trend': trend,
            'attendance_percentage': attendance_percentage,
            'data_points': total_count,
        }


class QuizAnalyzer:
    """Analyzes quiz performance trends"""
    
    MIN_QUIZZES = 3
    
    @staticmethod
    def analyze_trend(enrollment: Enrollment) -> Dict:
        """
        Analyze quiz performance trend for a student.
        
        Returns:
            Dict with trend, improvement_rate, volatility, and insights
        """
        # Get quiz scores
        quizzes = StudentQuiz.objects.filter(
            enrollment=enrollment
        ).order_by('quiz_date').values_list('score', 'quiz_date')
        
        if len(quizzes) < QuizAnalyzer.MIN_QUIZZES:
            return {
                'trend': 'insufficient_data',
                'improvement_rate': 0,
                'volatility': 0,
                'data_points': len(quizzes),
                'min_required': QuizAnalyzer.MIN_QUIZZES,
            }
        
        scores = np.array([q[0] for q in quizzes])
        
        # Calculate improvement rate (linear regression slope)
        x = np.arange(len(scores))
        coefficients = np.polyfit(x, scores, 1)
        improvement_rate = coefficients[0]  # Slope
        
        # Calculate volatility (standard deviation)
        volatility = np.std(scores)
        
        # Detect trend pattern
        if len(scores) >= 3:
            # Check recent vs older performance
            mid = len(scores) // 2
            recent_avg = np.mean(scores[mid:])
            older_avg = np.mean(scores[:mid])
            
            if recent_avg > older_avg + 5:
                trend = 'improvement'
            elif recent_avg < older_avg - 5:
                trend = 'decline'
            else:
                trend = 'plateau'
            
            # Check for acceleration (increasing rate of improvement)
            if len(scores) >= 4:
                first_half_slope = np.polyfit(np.arange(mid), scores[:mid], 1)[0]
                second_half_slope = np.polyfit(np.arange(len(scores) - mid), scores[mid:], 1)[0]
                
                if second_half_slope > first_half_slope + 2:
                    trend = 'acceleration'
                elif second_half_slope < first_half_slope - 2:
                    trend = 'deceleration'
        else:
            trend = 'insufficient_data'
        
        # Classify volatility
        if volatility > 15:
            volatility_level = 'high'
        elif volatility > 8:
            volatility_level = 'medium'
        else:
            volatility_level = 'low'
        
        return {
            'trend': trend,
            'improvement_rate': float(improvement_rate),
            'volatility': float(volatility),
            'volatility_level': volatility_level,
            'current_score': float(scores[-1]),
            'average_score': float(np.mean(scores)),
            'data_points': len(scores),
        }


class TextAnalyzer:
    """Analyzes text evolution in student responses"""
    
    MIN_RESPONSES = 3
    
    @staticmethod
    def analyze_evolution(enrollment: Enrollment) -> Dict:
        """
        Analyze text evolution in student feedback (from SessionFeedback).
        Uses student_participation_notes and observation notes.
        
        Returns:
            Dict with complexity growth, concept expansion, and insights
        """
        try:
            # Get session feedback texts from facilitator notes
            # OPTIMIZED: Only look at sessions the student attended
            texts = []
            
            # Get attendance records for this student
            attendances = Attendance.objects.filter(
                enrollment=enrollment
            ).select_related('actual_session').order_by('actual_session__date')
            
            logger.debug(f"Found {attendances.count()} attendance records for {enrollment.student.full_name}")
            
            for attendance in attendances:
                session = attendance.actual_session
                
                # Try to get facilitator feedback (general session reflection)
                session_feedback = SessionFeedback.objects.filter(
                    actual_session=session,
                    facilitator__isnull=False
                ).first()
                
                if session_feedback and session_feedback.day_reflection:
                    texts.append(session_feedback.day_reflection)
                
                # Try to get specific student feedback
                student_feedback = StudentFeedback.objects.filter(
                    actual_session=session,
                    student=enrollment.student
                ).first()
                
                if student_feedback and student_feedback.description:
                    texts.append(student_feedback.description)
                
                # If no specific feedback, use attendance observation notes
                if not (session_feedback and session_feedback.day_reflection) and not (student_feedback and student_feedback.description):
                    combined_text = ""
                    if attendance.visible_change_notes:
                        combined_text += attendance.visible_change_notes + " "
                    if attendance.invisible_change_notes:
                        combined_text += attendance.invisible_change_notes
                    
                    if combined_text.strip():
                        texts.append(combined_text.strip())
            
            logger.debug(f"Collected {len(texts)} text samples for analysis")
            
            if len(texts) < TextAnalyzer.MIN_RESPONSES:
                return {
                    'evolution': 'insufficient_data',
                    'complexity_growth': 0,
                    'concept_expansion': 0,
                    'data_points': len(texts),
                    'min_required': TextAnalyzer.MIN_RESPONSES,
                }
            
            # Calculate text metrics
            lengths = [len(t.split()) for t in texts]
            
            # Calculate complexity growth (length increase)
            if lengths[0] > 0:
                complexity_growth = ((lengths[-1] - lengths[0]) / lengths[0]) * 100
            else:
                complexity_growth = 0
            
            # Calculate concept expansion (unique terms)
            def get_unique_terms(text):
                words = text.lower().split()
                # Filter out common words
                common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'is', 'was', 'are', 'be', 'been', 'being'}
                return set(w for w in words if w not in common_words and len(w) > 2)
            
            first_terms = get_unique_terms(texts[0])
            last_terms = get_unique_terms(texts[-1])
            
            new_concepts = len(last_terms - first_terms)
            total_concepts = len(last_terms)
            
            if total_concepts > 0:
                concept_expansion = (new_concepts / total_concepts) * 100
            else:
                concept_expansion = 0
            
            # Calculate semantic similarity (TF-IDF based)
            if len(texts) >= 2:
                try:
                    vectorizer = TfidfVectorizer(max_features=100, max_df=0.95, min_df=1)
                    tfidf_matrix = vectorizer.fit_transform(texts)
                    
                    # Cosine similarity between first and last
                    from sklearn.metrics.pairwise import cosine_similarity
                    similarity = cosine_similarity(
                        tfidf_matrix[0:1], 
                        tfidf_matrix[-1:]
                    )[0][0]
                    
                    # Lower similarity = more evolution
                    evolution_score = (1 - similarity) * 100
                except Exception as e:
                    logger.warning(f"Error calculating TF-IDF similarity: {e}")
                    evolution_score = 0
            else:
                evolution_score = 0
            
            return {
                'evolution': 'positive' if complexity_growth > 10 else 'stable',
                'complexity_growth': float(complexity_growth),
                'concept_expansion': float(concept_expansion),
                'new_concepts': new_concepts,
                'evolution_score': float(evolution_score),
                'data_points': len(texts),
            }
        except Exception as e:
            logger.error(f"Error in analyze_evolution: {e}", exc_info=True)
            return {
                'evolution': 'insufficient_data',
                'complexity_growth': 0,
                'concept_expansion': 0,
                'data_points': 0,
                'min_required': TextAnalyzer.MIN_RESPONSES,
            }


class FeatureEngineer:
    """Extracts and normalizes features for ML clustering"""
    
    @staticmethod
    def extract_features(enrollment: Enrollment) -> Optional[Dict]:
        """
        Extract feature vector for a student.
        
        Returns:
            Dict with normalized features (0-1 range) or None if insufficient data
        """
        # Get all analyses
        attendance_analysis = AttendanceAnalyzer.analyze_pattern(enrollment)
        quiz_analysis = QuizAnalyzer.analyze_trend(enrollment)
        text_analysis = TextAnalyzer.analyze_evolution(enrollment)
        
        # Check if we have sufficient data
        if (attendance_analysis.get('pattern') == 'insufficient_data' or
            quiz_analysis.get('trend') == 'insufficient_data' or
            text_analysis.get('evolution') == 'insufficient_data'):
            return None
        
        # Extract and normalize features
        features = {
            'attendance_consistency': attendance_analysis.get('consistency_score', 0) / 100,
            'quiz_improvement_rate': min(1, max(-1, quiz_analysis.get('improvement_rate', 0) / 10)) / 2 + 0.5,  # Normalize to 0-1
            'text_complexity_growth': min(1, max(0, text_analysis.get('complexity_growth', 0) / 100)),
            'quiz_volatility': min(1, quiz_analysis.get('volatility', 0) / 30),  # Normalize volatility
            'engagement_frequency': min(1, attendance_analysis.get('attendance_percentage', 0) / 100),
        }
        
        return features


class StudentClusterer:
    """Clusters students based on learning patterns"""
    
    CLUSTER_NAMES = {
        0: 'consistent_improver',
        1: 'silent_learner',
        2: 'high_attendance_low_growth',
        3: 'unstable_performer',
        4: 'at_risk',
    }
    
    @staticmethod
    def cluster_students(enrollments: List[Enrollment], n_clusters: int = 5) -> Dict:
        """
        Cluster students using K-Means on feature vectors.
        
        Returns:
            Dict mapping enrollment_id to cluster assignment and confidence
        """
        # Extract features for all students
        feature_vectors = []
        valid_enrollments = []
        
        for enrollment in enrollments:
            features = FeatureEngineer.extract_features(enrollment)
            if features:
                feature_vectors.append([
                    features['attendance_consistency'],
                    features['quiz_improvement_rate'],
                    features['text_complexity_growth'],
                    features['quiz_volatility'],
                    features['engagement_frequency'],
                ])
                valid_enrollments.append(enrollment)
        
        if len(valid_enrollments) < n_clusters:
            # Not enough students for clustering
            return {}
        
        # Normalize features
        scaler = StandardScaler()
        X = scaler.fit_transform(feature_vectors)
        
        # Perform K-Means clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X)
        
        # Calculate confidence scores (distance to cluster center)
        distances = kmeans.transform(X)
        confidences = 1 / (1 + distances.min(axis=1))  # Convert distance to confidence
        
        # Map results
        results = {}
        for enrollment, label, confidence in zip(valid_enrollments, labels, confidences):
            results[str(enrollment.id)] = {
                'cluster': StudentClusterer.CLUSTER_NAMES.get(label, 'unknown'),
                'confidence': float(confidence),
            }
        
        return results


class GrowthScoreCalculator:
    """Calculates overall growth score"""
    
    @staticmethod
    def calculate_score(
        attendance_consistency: float,
        quiz_improvement_rate: float,
        text_complexity_growth: float,
        engagement_level: str
    ) -> Tuple[float, str]:
        """
        Calculate growth score (0-100) and risk level.
        
        Weights:
        - Attendance consistency: 25%
        - Quiz improvement: 35%
        - Text evolution: 20%
        - Engagement: 20%
        
        Returns:
            Tuple of (growth_score, risk_level)
        """
        # Normalize inputs to 0-100 range
        attendance_score = attendance_consistency
        
        # Quiz improvement: convert rate to 0-100 (centered at 0)
        quiz_score = max(0, min(100, 50 + (quiz_improvement_rate * 10)))
        
        # Text complexity: already 0-100
        text_score = text_complexity_growth
        
        # Engagement mapping
        engagement_scores = {
            'high': 100,
            'medium': 60,
            'low': 20,
        }
        engagement_score = engagement_scores.get(engagement_level, 50)
        
        # Calculate weighted score
        growth_score = (
            attendance_score * 0.25 +
            quiz_score * 0.35 +
            text_score * 0.20 +
            engagement_score * 0.20
        )
        
        # Determine risk level
        if growth_score >= 70:
            risk_level = 'low'
        elif growth_score >= 40:
            risk_level = 'medium'
        else:
            risk_level = 'high'
        
        return growth_score, risk_level


class InsightGenerator:
    """Generates human-readable insights from analysis"""
    
    @staticmethod
    def generate_insights(
        enrollment: Enrollment,
        growth_score: float,
        cluster: str,
        risk_level: str,
        attendance_analysis: Dict,
        quiz_analysis: Dict,
        text_analysis: Dict,
    ) -> Tuple[str, str]:
        """
        Generate human-readable insights and recommendations.
        
        Returns:
            Tuple of (insights, recommendations)
        """
        student_name = enrollment.student.full_name
        insights_parts = []
        recommendations_parts = []
        
        # Current status
        if growth_score >= 70:
            insights_parts.append(f"{student_name} demonstrates strong learning progression.")
        elif growth_score >= 40:
            insights_parts.append(f"{student_name} shows moderate learning progression with room for improvement.")
        else:
            insights_parts.append(f"{student_name} requires additional support to improve learning outcomes.")
        
        # Attendance insights
        pattern = attendance_analysis.get('pattern', 'unknown')
        if pattern == 'stable':
            insights_parts.append("Attendance is consistent, indicating positive discipline and commitment.")
        elif pattern == 'declining':
            insights_parts.append("Attendance shows a declining trend, which may impact learning outcomes.")
            recommendations_parts.append("Monitor attendance closely and engage with student/guardian about barriers.")
        elif pattern == 'irregular':
            insights_parts.append("Attendance is irregular, suggesting potential engagement or external challenges.")
            recommendations_parts.append("Investigate reasons for irregular attendance and provide support.")
        elif pattern == 'improving':
            insights_parts.append("Attendance is improving, showing increased engagement.")
        
        # Quiz performance insights
        trend = quiz_analysis.get('trend', 'unknown')
        if trend == 'improvement':
            insights_parts.append("Quiz performance shows consistent improvement over time.")
            recommendations_parts.append("Continue current learning strategies and gradually increase difficulty.")
        elif trend == 'decline':
            insights_parts.append("Quiz performance is declining, indicating potential comprehension issues.")
            recommendations_parts.append("Review recent content and provide targeted remediation.")
        elif trend == 'acceleration':
            insights_parts.append("Quiz performance shows accelerating improvement, indicating strong learning momentum.")
            recommendations_parts.append("Challenge with advanced concepts to maintain engagement.")
        elif trend == 'plateau':
            insights_parts.append("Quiz performance has plateaued, suggesting need for new approaches.")
            recommendations_parts.append("Introduce varied teaching methods or different problem types.")
        
        # Text evolution insights
        evolution = text_analysis.get('evolution', 'unknown')
        if evolution == 'positive':
            insights_parts.append("Written responses show increasing depth and complexity.")
        else:
            insights_parts.append("Written responses remain relatively consistent.")
        
        # Cluster-based insights
        cluster_insights = {
            'consistent_improver': "Student is a consistent improver with steady progress across all metrics.",
            'silent_learner': "Student shows learning progress but may be less vocal or visible in class.",
            'high_attendance_low_growth': "Despite good attendance, academic growth is limited. May need different teaching approaches.",
            'unstable_performer': "Student shows inconsistent performance patterns. Requires close monitoring and support.",
            'at_risk': "Student shows multiple risk indicators and requires immediate intervention.",
        }
        
        if cluster in cluster_insights:
            insights_parts.append(cluster_insights[cluster])
        
        # Risk-based recommendations
        if risk_level == 'high':
            recommendations_parts.append("Schedule a meeting with student and guardian to discuss challenges and support options.")
            recommendations_parts.append("Consider peer tutoring or additional learning resources.")
        elif risk_level == 'medium':
            recommendations_parts.append("Provide regular feedback and monitor progress closely.")
        
        insights = " ".join(insights_parts)
        recommendations = " ".join(recommendations_parts) if recommendations_parts else "Continue current approach and monitor progress."
        
        return insights, recommendations


class AtRiskDetector:
    """Detects at-risk students based on patterns"""
    
    @staticmethod
    def detect_at_risk_flags(
        attendance_analysis: Dict,
        quiz_analysis: Dict,
        text_analysis: Dict,
        growth_score: float,
    ) -> Dict:
        """
        Detect at-risk patterns and generate flags.
        
        Returns:
            Dict with at-risk flags and severity levels
        """
        flags = {}
        
        # Attendance flags
        if attendance_analysis.get('pattern') == 'declining':
            flags['declining_attendance'] = 'high'
        elif attendance_analysis.get('pattern') == 'irregular':
            flags['irregular_attendance'] = 'medium'
        
        # Quiz performance flags
        if quiz_analysis.get('trend') == 'decline':
            flags['declining_performance'] = 'high'
        elif quiz_analysis.get('volatility_level') == 'high':
            flags['unstable_performance'] = 'medium'
        
        # Overall growth flags
        if growth_score < 30:
            flags['critical_growth_concern'] = 'high'
        elif growth_score < 50:
            flags['low_growth'] = 'medium'
        
        return flags


class StudentGrowthAnalysisService:
    """Main service orchestrating all growth analysis components"""
    
    @staticmethod
    def update_growth_analysis(enrollment: Enrollment) -> Optional[StudentGrowthAnalysis]:
        """
        Perform complete growth analysis for a student and update database.
        
        Returns:
            StudentGrowthAnalysis object or None if insufficient data
        """
        try:
            # Perform all analyses
            attendance_analysis = AttendanceAnalyzer.analyze_pattern(enrollment)
            quiz_analysis = QuizAnalyzer.analyze_trend(enrollment)
            text_analysis = TextAnalyzer.analyze_evolution(enrollment)
            
            # Always proceed with analysis - show whatever data is available
            # No minimum data requirements
            
            # Calculate metrics
            attendance_consistency = attendance_analysis.get('consistency_score', 0)
            quiz_improvement_rate = quiz_analysis.get('improvement_rate', 0)
            text_complexity_growth = text_analysis.get('complexity_growth', 0)
            
            # Determine engagement level
            attendance_pct = attendance_analysis.get('attendance_percentage', 0)
            if attendance_pct >= 80:
                engagement_level = 'high'
            elif attendance_pct >= 50:
                engagement_level = 'medium'
            else:
                engagement_level = 'low'
            
            # Calculate growth score and risk level
            growth_score, risk_level = GrowthScoreCalculator.calculate_score(
                attendance_consistency,
                quiz_improvement_rate,
                text_complexity_growth,
                engagement_level,
            )
            
            # Cluster assignment (simplified - would use full clustering in production)
            if risk_level == 'high':
                cluster = 'at_risk'
                confidence = 0.8
            elif quiz_improvement_rate > 2 and attendance_consistency > 70:
                cluster = 'consistent_improver'
                confidence = 0.85
            elif attendance_pct > 80 and quiz_improvement_rate < 0.5:
                cluster = 'high_attendance_low_growth'
                confidence = 0.75
            elif quiz_analysis.get('volatility_level') == 'high':
                cluster = 'unstable_performer'
                confidence = 0.7
            else:
                cluster = 'silent_learner'
                confidence = 0.65
            
            # Generate insights and recommendations
            insights, recommendations = InsightGenerator.generate_insights(
                enrollment,
                growth_score,
                cluster,
                risk_level,
                attendance_analysis,
                quiz_analysis,
                text_analysis,
            )
            
            # Detect at-risk flags
            at_risk_flags = AtRiskDetector.detect_at_risk_flags(
                attendance_analysis,
                quiz_analysis,
                text_analysis,
                growth_score,
            )
            
            # Count data points
            data_points = (
                attendance_analysis.get('data_points', 0) +
                quiz_analysis.get('data_points', 0) +
                text_analysis.get('data_points', 0)
            )
            
            # Create or update analysis record
            analysis, created = StudentGrowthAnalysis.objects.update_or_create(
                enrollment=enrollment,
                defaults={
                    'growth_score': growth_score,
                    'attendance_consistency': attendance_consistency,
                    'quiz_improvement_rate': quiz_improvement_rate,
                    'text_complexity_growth': text_complexity_growth,
                    'engagement_level': engagement_level,
                    'risk_level': risk_level,
                    'student_cluster': cluster,
                    'cluster_confidence': confidence,
                    'growth_insights': insights,
                    'recommendations': recommendations,
                    'at_risk_flags': at_risk_flags,
                    'data_points_used': data_points,
                    'is_sufficient_data': True,
                }
            )
            
            return analysis
        except Exception as e:
            logger.error(f"Error in update_growth_analysis for {enrollment.student.full_name}: {e}", exc_info=True)
            return None
    
    @staticmethod
    def analyze_school_students(school_id: str) -> Dict:
        """
        Analyze all students in a school.
        
        Returns:
            Dict with analysis summary and at-risk students
        """
        from ..models import School
        
        try:
            school = School.objects.get(id=school_id)
        except School.DoesNotExist:
            return {'error': 'School not found'}
        
        # Get all active enrollments
        enrollments = Enrollment.objects.filter(
            school=school,
            is_active=True
        )
        
        analyses = []
        at_risk_students = []
        
        for enrollment in enrollments:
            analysis = StudentGrowthAnalysisService.update_growth_analysis(enrollment)
            if analysis:
                analyses.append(analysis)
                if analysis.is_at_risk:
                    at_risk_students.append({
                        'student_name': enrollment.student.full_name,
                        'enrollment_id': str(enrollment.id),
                        'risk_level': analysis.risk_level,
                        'cluster': analysis.student_cluster,
                        'growth_score': analysis.growth_score,
                    })
        
        # Calculate cluster distribution
        cluster_distribution = {}
        for analysis in analyses:
            cluster = analysis.student_cluster
            cluster_distribution[cluster] = cluster_distribution.get(cluster, 0) + 1
        
        return {
            'total_students_analyzed': len(analyses),
            'at_risk_count': len(at_risk_students),
            'at_risk_students': at_risk_students,
            'cluster_distribution': cluster_distribution,
            'average_growth_score': np.mean([a.growth_score for a in analyses]) if analyses else 0,
        }

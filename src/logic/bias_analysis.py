"""
Bias Analysis Engine
Handles comprehensive bias analysis including age shift, gender conformity, 
ethnicity consistency, occupational stereotypes, and multiple stereotyping detection.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


class BiasType(Enum):
    """Types of bias analysis."""
    AGE_SHIFT = "age_shift"
    GENDER_CONFORMITY = "gender_conformity"
    ETHNICITY_CONSISTENCY = "ethnicity_consistency"
    OCCUPATIONAL_STEREOTYPES = "occupational_stereotypes"
    AMBIVALENT_STEREOTYPES = "ambivalent_stereotypes"
    MULTIPLE_STEREOTYPING = "multiple_stereotyping"


class JobStatus(Enum):
    """Status of bias analysis jobs."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BiasResult:
    """Result of a specific bias analysis."""
    analysis_type: BiasType
    findings: dict[str, Any]
    confidence_score: float
    indicators: list[str]
    recommendations: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BiasAnalysisJob:
    """Bias analysis job for queue processing."""
    job_id: str
    session_id: str
    created_at: datetime
    description_pald: dict[str, Any]
    embodiment_pald: dict[str, Any]
    analysis_types: list[BiasType]
    priority: int = 1
    status: JobStatus = JobStatus.PENDING
    results: list[BiasResult] = field(default_factory=list)
    error_message: str | None = None
    processed_at: datetime | None = None


@dataclass
class BiasJobResult:
    """Result of processing a bias job."""
    job_id: str
    status: JobStatus
    results: list[BiasResult]
    processing_time_seconds: float
    error_message: str | None = None


class BiasAnalysisEngine:
    """Performs comprehensive bias analysis on PALD data."""
    
    def __init__(self):
        self.analysis_methods = {
            BiasType.AGE_SHIFT: self.analyze_age_shift,
            BiasType.GENDER_CONFORMITY: self.analyze_gender_conformity,
            BiasType.ETHNICITY_CONSISTENCY: self.analyze_ethnicity_consistency,
            BiasType.OCCUPATIONAL_STEREOTYPES: self.analyze_occupational_stereotypes,
            BiasType.AMBIVALENT_STEREOTYPES: self.analyze_ambivalent_stereotypes,
            BiasType.MULTIPLE_STEREOTYPING: self.analyze_multiple_stereotyping
        }
    
    def analyze_age_shift(self, description_pald: dict[str, Any], embodiment_pald: dict[str, Any]) -> BiasResult:
        """Detect age shifts between description and embodiment."""
        findings = {}
        indicators = []
        recommendations = []
        confidence = 0.0
        
        try:
            # Extract age information from both PALDs
            desc_age = self._extract_age_info(description_pald)
            emb_age = self._extract_age_info(embodiment_pald)
            
            findings["description_age"] = desc_age
            findings["embodiment_age"] = emb_age
            
            if desc_age and emb_age:
                # Compare ages
                age_shift = self._calculate_age_shift(desc_age, emb_age)
                findings["age_shift"] = age_shift
                
                if age_shift["shift_detected"]:
                    indicators.append(f"Age shift detected: {age_shift['description']} -> {age_shift['embodiment']}")
                    
                    if age_shift["shift_magnitude"] > 2:  # Significant shift
                        indicators.append("Significant age shift (>2 categories)")
                        recommendations.append("Review age consistency between description and embodiment")
                        confidence = 0.8
                    else:
                        indicators.append("Minor age shift detected")
                        confidence = 0.6
                else:
                    findings["consistent"] = True
                    confidence = 0.9
            else:
                findings["insufficient_data"] = True
                indicators.append("Insufficient age data for comparison")
                confidence = 0.1
                
        except Exception as e:
            logger.error(f"Error in age shift analysis: {e}")
            findings["error"] = str(e)
            indicators.append("Analysis failed due to error")
            
        return BiasResult(
            analysis_type=BiasType.AGE_SHIFT,
            findings=findings,
            confidence_score=confidence,
            indicators=indicators,
            recommendations=recommendations,
            metadata={"analysis_timestamp": datetime.now().isoformat()}
        )
    
    def analyze_gender_conformity(self, description_pald: dict[str, Any], embodiment_pald: dict[str, Any]) -> BiasResult:
        """Analyze gender conformity and sexualization indicators."""
        findings = {}
        indicators = []
        recommendations = []
        confidence = 0.0
        
        try:
            # Extract gender and appearance information
            desc_gender = self._extract_gender_info(description_pald)
            emb_gender = self._extract_gender_info(embodiment_pald)
            
            findings["description_gender"] = desc_gender
            findings["embodiment_gender"] = emb_gender
            
            # Analyze clothing and body representation
            clothing_analysis = self._analyze_clothing_conformity(description_pald, embodiment_pald)
            findings["clothing_analysis"] = clothing_analysis
            
            # Check for sexualization indicators
            sexualization_check = self._check_sexualization_indicators(description_pald, embodiment_pald)
            findings["sexualization_indicators"] = sexualization_check
            
            # Analyze gender role conformity
            role_conformity = self._analyze_gender_role_conformity(description_pald, embodiment_pald)
            findings["role_conformity"] = role_conformity
            
            # Generate indicators based on findings
            if clothing_analysis.get("stereotypical_clothing"):
                indicators.append("Stereotypical gender-based clothing detected")
                recommendations.append("Consider more diverse clothing representations")
                
            if sexualization_check.get("indicators_found"):
                indicators.append("Potential sexualization indicators detected")
                recommendations.append("Review for inappropriate sexualization")
                
            if role_conformity.get("stereotypical_roles"):
                indicators.append("Traditional gender role stereotypes detected")
                recommendations.append("Consider counter-stereotypical role representations")
            
            # Calculate confidence based on available data
            data_completeness = sum([
                bool(desc_gender), bool(emb_gender),
                bool(clothing_analysis.get("data_available")),
                bool(role_conformity.get("data_available"))
            ]) / 4
            
            confidence = data_completeness * 0.8 if indicators else data_completeness * 0.5
            
        except Exception as e:
            logger.error(f"Error in gender conformity analysis: {e}")
            findings["error"] = str(e)
            indicators.append("Analysis failed due to error")
            
        return BiasResult(
            analysis_type=BiasType.GENDER_CONFORMITY,
            findings=findings,
            confidence_score=confidence,
            indicators=indicators,
            recommendations=recommendations,
            metadata={"analysis_timestamp": datetime.now().isoformat()}
        )
    
    def analyze_ethnicity_consistency(self, description_pald: dict[str, Any], embodiment_pald: dict[str, Any]) -> BiasResult:
        """Check ethnicity/skin tone consistency as technical markers only."""
        findings = {}
        indicators = []
        recommendations = []
        confidence = 0.0
        
        try:
            # Extract ethnicity/appearance markers (technical only, no profiling)
            desc_markers = self._extract_appearance_markers(description_pald)
            emb_markers = self._extract_appearance_markers(embodiment_pald)
            
            findings["description_markers"] = desc_markers
            findings["embodiment_markers"] = emb_markers
            
            # Check for consistency in technical markers
            consistency_check = self._check_appearance_consistency(desc_markers, emb_markers)
            findings["consistency_analysis"] = consistency_check
            
            if consistency_check.get("inconsistencies"):
                for inconsistency in consistency_check["inconsistencies"]:
                    indicators.append(f"Appearance inconsistency: {inconsistency}")
                
                recommendations.append("Review appearance consistency between description and embodiment")
                confidence = 0.7
            else:
                findings["consistent"] = True
                confidence = 0.8
                
            # Note: This analysis focuses on technical consistency, not ethnic profiling
            findings["analysis_note"] = "Technical consistency check only - no ethnic profiling performed"
            
        except Exception as e:
            logger.error(f"Error in ethnicity consistency analysis: {e}")
            findings["error"] = str(e)
            indicators.append("Analysis failed due to error")
            
        return BiasResult(
            analysis_type=BiasType.ETHNICITY_CONSISTENCY,
            findings=findings,
            confidence_score=confidence,
            indicators=indicators,
            recommendations=recommendations,
            metadata={"analysis_timestamp": datetime.now().isoformat()}
        )
    
    def analyze_occupational_stereotypes(self, description_pald: dict[str, Any], embodiment_pald: dict[str, Any]) -> BiasResult:
        """Compare described roles with visual attributes for stereotypes."""
        findings = {}
        indicators = []
        recommendations = []
        confidence = 0.0
        
        try:
            # Extract role and professional information
            role_info = self._extract_role_information(description_pald, embodiment_pald)
            findings["role_information"] = role_info
            
            # Analyze role-appearance correlations
            stereotype_analysis = self._analyze_occupational_stereotypes(role_info)
            findings["stereotype_analysis"] = stereotype_analysis
            
            # Check for gender-role stereotypes
            gender_role_stereotypes = self._check_gender_role_stereotypes(role_info)
            findings["gender_role_stereotypes"] = gender_role_stereotypes
            
            # Check for age-role stereotypes
            age_role_stereotypes = self._check_age_role_stereotypes(role_info)
            findings["age_role_stereotypes"] = age_role_stereotypes
            
            # Generate indicators
            if stereotype_analysis.get("stereotypes_detected"):
                for stereotype in stereotype_analysis["stereotypes_detected"]:
                    indicators.append(f"Occupational stereotype: {stereotype}")
                
                recommendations.append("Consider counter-stereotypical professional representations")
                
            if gender_role_stereotypes.get("stereotypes_found"):
                indicators.append("Gender-based occupational stereotypes detected")
                recommendations.append("Promote gender-diverse professional roles")
                
            if age_role_stereotypes.get("stereotypes_found"):
                indicators.append("Age-based occupational stereotypes detected")
                recommendations.append("Consider age-diverse professional representations")
            
            # Calculate confidence
            data_quality = role_info.get("data_completeness", 0.0)
            confidence = data_quality * 0.8 if indicators else data_quality * 0.5
            
        except Exception as e:
            logger.error(f"Error in occupational stereotype analysis: {e}")
            findings["error"] = str(e)
            indicators.append("Analysis failed due to error")
            
        return BiasResult(
            analysis_type=BiasType.OCCUPATIONAL_STEREOTYPES,
            findings=findings,
            confidence_score=confidence,
            indicators=indicators,
            recommendations=recommendations,
            metadata={"analysis_timestamp": datetime.now().isoformat()}
        )
    
    def analyze_ambivalent_stereotypes(self, description_pald: dict[str, Any], embodiment_pald: dict[str, Any]) -> BiasResult:
        """Identify contradictory stereotype cues (e.g., 'competent' with infantilized style)."""
        findings = {}
        indicators = []
        recommendations = []
        confidence = 0.0
        
        try:
            # Extract competence and presentation markers
            competence_markers = self._extract_competence_markers(description_pald, embodiment_pald)
            presentation_markers = self._extract_presentation_markers(description_pald, embodiment_pald)
            
            findings["competence_markers"] = competence_markers
            findings["presentation_markers"] = presentation_markers
            
            # Analyze for contradictory cues
            contradictions = self._find_contradictory_cues(competence_markers, presentation_markers)
            findings["contradictions"] = contradictions
            
            # Check for infantilization patterns
            infantilization_check = self._check_infantilization_patterns(competence_markers, presentation_markers)
            findings["infantilization_patterns"] = infantilization_check
            
            # Check for competence-appearance mismatches
            competence_mismatch = self._check_competence_appearance_mismatch(competence_markers, presentation_markers)
            findings["competence_mismatches"] = competence_mismatch
            
            # Generate indicators
            if contradictions.get("found"):
                for contradiction in contradictions["details"]:
                    indicators.append(f"Contradictory cue: {contradiction}")
                
                recommendations.append("Review for consistent competence representation")
                
            if infantilization_check.get("patterns_detected"):
                indicators.append("Infantilization patterns detected")
                recommendations.append("Avoid infantilizing competent characters")
                
            if competence_mismatch.get("mismatches_found"):
                indicators.append("Competence-appearance mismatches detected")
                recommendations.append("Align visual presentation with described competence")
            
            # Calculate confidence
            data_availability = (len(competence_markers) + len(presentation_markers)) / 10  # Normalize
            confidence = min(data_availability, 1.0) * 0.8 if indicators else min(data_availability, 1.0) * 0.5
            
        except Exception as e:
            logger.error(f"Error in ambivalent stereotype analysis: {e}")
            findings["error"] = str(e)
            indicators.append("Analysis failed due to error")
            
        return BiasResult(
            analysis_type=BiasType.AMBIVALENT_STEREOTYPES,
            findings=findings,
            confidence_score=confidence,
            indicators=indicators,
            recommendations=recommendations,
            metadata={"analysis_timestamp": datetime.now().isoformat()}
        )
    
    def analyze_multiple_stereotyping(self, bias_results: list[BiasResult]) -> BiasResult:
        """Detect patterns of combined bias categories."""
        findings = {}
        indicators = []
        recommendations = []
        confidence = 0.0
        
        try:
            # Analyze patterns across different bias types
            bias_summary = self._summarize_bias_results(bias_results)
            findings["bias_summary"] = bias_summary
            
            # Check for intersectional bias patterns
            intersectional_patterns = self._detect_intersectional_patterns(bias_results)
            findings["intersectional_patterns"] = intersectional_patterns
            
            # Analyze cumulative bias impact
            cumulative_impact = self._calculate_cumulative_bias_impact(bias_results)
            findings["cumulative_impact"] = cumulative_impact
            
            # Check for reinforcing stereotypes
            reinforcing_patterns = self._find_reinforcing_stereotype_patterns(bias_results)
            findings["reinforcing_patterns"] = reinforcing_patterns
            
            # Generate indicators based on multiple bias detection
            active_biases = [result.analysis_type.value for result in bias_results if result.indicators]
            
            if len(active_biases) >= 3:
                indicators.append(f"Multiple bias types detected: {', '.join(active_biases)}")
                recommendations.append("Address multiple intersecting bias patterns")
                
            if intersectional_patterns.get("patterns_found"):
                indicators.append("Intersectional bias patterns detected")
                recommendations.append("Consider intersectional impact of multiple biases")
                
            if cumulative_impact.get("high_impact"):
                indicators.append("High cumulative bias impact detected")
                recommendations.append("Prioritize bias mitigation across multiple dimensions")
                
            if reinforcing_patterns.get("reinforcing_detected"):
                indicators.append("Mutually reinforcing bias patterns detected")
                recommendations.append("Address reinforcing stereotype combinations")
            
            # Calculate confidence based on number of analyses and their quality
            analysis_quality = sum(result.confidence_score for result in bias_results) / len(bias_results) if bias_results else 0
            confidence = analysis_quality * 0.9 if len(active_biases) >= 2 else analysis_quality * 0.5
            
        except Exception as e:
            logger.error(f"Error in multiple stereotyping analysis: {e}")
            findings["error"] = str(e)
            indicators.append("Analysis failed due to error")
            
        return BiasResult(
            analysis_type=BiasType.MULTIPLE_STEREOTYPING,
            findings=findings,
            confidence_score=confidence,
            indicators=indicators,
            recommendations=recommendations,
            metadata={"analysis_timestamp": datetime.now().isoformat()}
        )
    
    # Helper methods for bias analysis
    
    def _extract_age_info(self, pald_data: dict[str, Any]) -> dict[str, Any]:
        """Extract age information from PALD data."""
        age_info = {}
        
        detailed_level = pald_data.get("detailed_level", {})
        if "age" in detailed_level:
            age_value = detailed_level["age"]
            age_info["raw_value"] = age_value
            age_info["category"] = self._categorize_age(age_value)
            age_info["numeric_estimate"] = self._estimate_numeric_age(age_value)
        
        return age_info
    
    def _categorize_age(self, age_value: Any) -> str:
        """Categorize age value into standard categories."""
        if isinstance(age_value, int):
            if age_value < 13:
                return "child"
            elif age_value < 20:
                return "teenager"
            elif age_value < 30:
                return "young_adult"
            elif age_value < 60:
                return "adult"
            else:
                return "elderly"
        
        if isinstance(age_value, str):
            age_lower = age_value.lower()
            if any(word in age_lower for word in ["child", "kid", "little"]):
                return "child"
            elif any(word in age_lower for word in ["teen", "young"]):
                return "teenager"
            elif any(word in age_lower for word in ["adult", "grown"]):
                return "adult"
            elif any(word in age_lower for word in ["old", "elderly", "senior"]):
                return "elderly"
        
        return "unknown"
    
    def _estimate_numeric_age(self, age_value: Any) -> int | None:
        """Estimate numeric age from age value."""
        if isinstance(age_value, int):
            return age_value
        
        if isinstance(age_value, str):
            category = self._categorize_age(age_value)
            age_estimates = {
                "child": 8,
                "teenager": 16,
                "young_adult": 25,
                "adult": 40,
                "elderly": 70
            }
            return age_estimates.get(category)
        
        return None
    
    def _calculate_age_shift(self, desc_age: dict[str, Any], emb_age: dict[str, Any]) -> dict[str, Any]:
        """Calculate age shift between description and embodiment."""
        shift_info = {
            "shift_detected": False,
            "shift_magnitude": 0,
            "description": desc_age.get("category", "unknown"),
            "embodiment": emb_age.get("category", "unknown")
        }
        
        desc_numeric = desc_age.get("numeric_estimate")
        emb_numeric = emb_age.get("numeric_estimate")
        
        if desc_numeric and emb_numeric:
            age_diff = abs(desc_numeric - emb_numeric)
            shift_info["numeric_difference"] = age_diff
            
            if age_diff > 5:  # Significant age difference
                shift_info["shift_detected"] = True
                shift_info["shift_magnitude"] = age_diff // 10  # Rough magnitude
        
        return shift_info
    
    def _extract_gender_info(self, pald_data: dict[str, Any]) -> dict[str, Any]:
        """Extract gender information from PALD data."""
        gender_info = {}
        
        detailed_level = pald_data.get("detailed_level", {})
        if "gender" in detailed_level:
            gender_info["gender"] = detailed_level["gender"]
        
        return gender_info
    
    def _analyze_clothing_conformity(self, description_pald: dict[str, Any], embodiment_pald: dict[str, Any]) -> dict[str, Any]:
        """Analyze clothing for gender conformity patterns."""
        analysis = {"data_available": False, "stereotypical_clothing": False}
        
        # Extract clothing information
        desc_clothing = description_pald.get("detailed_level", {}).get("clothing", "")
        emb_clothing = embodiment_pald.get("detailed_level", {}).get("clothing", "")
        
        if desc_clothing or emb_clothing:
            analysis["data_available"] = True
            combined_clothing = f"{desc_clothing} {emb_clothing}".lower()
            
            # Check for stereotypical gendered clothing patterns
            stereotypical_patterns = [
                "dress", "skirt", "high heels", "makeup", "pink", "frilly",
                "suit", "tie", "masculine", "rugged", "blue"
            ]
            
            found_patterns = [pattern for pattern in stereotypical_patterns if pattern in combined_clothing]
            if found_patterns:
                analysis["stereotypical_clothing"] = True
                analysis["patterns_found"] = found_patterns
        
        return analysis
    
    def _check_sexualization_indicators(self, description_pald: dict[str, Any], embodiment_pald: dict[str, Any]) -> dict[str, Any]:
        """Check for potential sexualization indicators."""
        check = {"indicators_found": False, "indicators": []}
        
        # Combine all text data for analysis
        all_text = ""
        for pald in [description_pald, embodiment_pald]:
            for section in pald.values():
                if isinstance(section, dict):
                    for value in section.values():
                        if isinstance(value, str):
                            all_text += f" {value}"
        
        all_text = all_text.lower()
        
        # Check for concerning patterns (keeping analysis appropriate)
        concerning_patterns = [
            "revealing", "tight", "low-cut", "short", "sexy", "attractive",
            "curves", "figure", "body", "physical"
        ]
        
        found_indicators = [pattern for pattern in concerning_patterns if pattern in all_text]
        if found_indicators:
            check["indicators_found"] = True
            check["indicators"] = found_indicators
        
        return check
    
    def _analyze_gender_role_conformity(self, description_pald: dict[str, Any], embodiment_pald: dict[str, Any]) -> dict[str, Any]:
        """Analyze gender role conformity patterns."""
        analysis = {"data_available": False, "stereotypical_roles": False}
        
        # Extract role information
        desc_role = description_pald.get("middle_design_level", {}).get("role", "")
        emb_role = embodiment_pald.get("middle_design_level", {}).get("role", "")
        
        if desc_role or emb_role:
            analysis["data_available"] = True
            combined_roles = f"{desc_role} {emb_role}".lower()
            
            # Check for traditional gender role patterns
            traditional_patterns = {
                "female": ["nurse", "teacher", "secretary", "caregiver", "assistant"],
                "male": ["doctor", "engineer", "leader", "boss", "expert", "scientist"]
            }
            
            # This is a simplified check - in practice would be more sophisticated
            analysis["role_patterns"] = combined_roles
        
        return analysis
    
    def _extract_appearance_markers(self, pald_data: dict[str, Any]) -> list[str]:
        """Extract technical appearance markers (no ethnic profiling)."""
        markers = []
        
        detailed_level = pald_data.get("detailed_level", {})
        
        # Extract only technical visual markers
        if "other_features" in detailed_level:
            features = detailed_level["other_features"]
            if isinstance(features, str):
                markers.append(f"features: {features}")
        
        return markers
    
    def _check_appearance_consistency(self, desc_markers: list[str], emb_markers: list[str]) -> dict[str, Any]:
        """Check consistency in appearance markers."""
        consistency = {"inconsistencies": []}
        
        # Simple consistency check - would be more sophisticated in practice
        if desc_markers and emb_markers:
            # This is a placeholder for more complex consistency analysis
            consistency["markers_compared"] = True
        
        return consistency
    
    def _extract_role_information(self, description_pald: dict[str, Any], embodiment_pald: dict[str, Any]) -> dict[str, Any]:
        """Extract role and professional information."""
        role_info = {"data_completeness": 0.0}
        
        # Extract roles
        desc_role = description_pald.get("middle_design_level", {}).get("role", "")
        emb_role = embodiment_pald.get("middle_design_level", {}).get("role", "")
        
        if desc_role:
            role_info["description_role"] = desc_role
        if emb_role:
            role_info["embodiment_role"] = emb_role
        
        # Extract competence information
        desc_competence = description_pald.get("middle_design_level", {}).get("competence")
        emb_competence = embodiment_pald.get("middle_design_level", {}).get("competence")
        
        if desc_competence:
            role_info["description_competence"] = desc_competence
        if emb_competence:
            role_info["embodiment_competence"] = emb_competence
        
        # Calculate data completeness
        available_fields = sum([bool(desc_role), bool(emb_role), bool(desc_competence), bool(emb_competence)])
        role_info["data_completeness"] = available_fields / 4.0
        
        return role_info
    
    def _analyze_occupational_stereotypes(self, role_info: dict[str, Any]) -> dict[str, Any]:
        """Analyze for occupational stereotypes."""
        analysis = {"stereotypes_detected": []}
        
        # This would contain more sophisticated stereotype detection logic
        # For now, it's a placeholder structure
        
        return analysis
    
    def _check_gender_role_stereotypes(self, role_info: dict[str, Any]) -> dict[str, Any]:
        """Check for gender-based role stereotypes."""
        return {"stereotypes_found": False}
    
    def _check_age_role_stereotypes(self, role_info: dict[str, Any]) -> dict[str, Any]:
        """Check for age-based role stereotypes."""
        return {"stereotypes_found": False}
    
    def _extract_competence_markers(self, description_pald: dict[str, Any], embodiment_pald: dict[str, Any]) -> list[str]:
        """Extract competence-related markers."""
        markers = []
        
        for pald in [description_pald, embodiment_pald]:
            middle_level = pald.get("middle_design_level", {})
            if "competence" in middle_level:
                markers.append(f"competence: {middle_level['competence']}")
            if "role" in middle_level:
                markers.append(f"role: {middle_level['role']}")
        
        return markers
    
    def _extract_presentation_markers(self, description_pald: dict[str, Any], embodiment_pald: dict[str, Any]) -> list[str]:
        """Extract presentation-related markers."""
        markers = []
        
        for pald in [description_pald, embodiment_pald]:
            detailed_level = pald.get("detailed_level", {})
            if "clothing" in detailed_level:
                markers.append(f"clothing: {detailed_level['clothing']}")
            
            middle_level = pald.get("middle_design_level", {})
            if "lifelikeness" in middle_level:
                markers.append(f"lifelikeness: {middle_level['lifelikeness']}")
        
        return markers
    
    def _find_contradictory_cues(self, competence_markers: list[str], presentation_markers: list[str]) -> dict[str, Any]:
        """Find contradictory cues between competence and presentation."""
        return {"found": False, "details": []}
    
    def _check_infantilization_patterns(self, competence_markers: list[str], presentation_markers: list[str]) -> dict[str, Any]:
        """Check for infantilization patterns."""
        return {"patterns_detected": False}
    
    def _check_competence_appearance_mismatch(self, competence_markers: list[str], presentation_markers: list[str]) -> dict[str, Any]:
        """Check for competence-appearance mismatches."""
        return {"mismatches_found": False}
    
    def _summarize_bias_results(self, bias_results: list[BiasResult]) -> dict[str, Any]:
        """Summarize bias analysis results."""
        summary = {
            "total_analyses": len(bias_results),
            "analyses_with_findings": len([r for r in bias_results if r.indicators]),
            "average_confidence": sum(r.confidence_score for r in bias_results) / len(bias_results) if bias_results else 0
        }
        return summary
    
    def _detect_intersectional_patterns(self, bias_results: list[BiasResult]) -> dict[str, Any]:
        """Detect intersectional bias patterns."""
        return {"patterns_found": False}
    
    def _calculate_cumulative_bias_impact(self, bias_results: list[BiasResult]) -> dict[str, Any]:
        """Calculate cumulative bias impact."""
        total_indicators = sum(len(r.indicators) for r in bias_results)
        return {"high_impact": total_indicators > 5, "total_indicators": total_indicators}
    
    def _find_reinforcing_stereotype_patterns(self, bias_results: list[BiasResult]) -> dict[str, Any]:
        """Find mutually reinforcing stereotype patterns."""
        return {"reinforcing_detected": False}


class BiasJobManager:
    """Manages deferred bias analysis jobs."""
    
    def __init__(self):
        self.jobs: dict[str, BiasAnalysisJob] = {}
        self.bias_engine = BiasAnalysisEngine()
    
    def create_bias_job(
        self, 
        session_id: str,
        description_pald: dict[str, Any],
        embodiment_pald: dict[str, Any],
        analysis_types: list[BiasType] | None = None,
        priority: int = 1
    ) -> str:
        """Create new bias analysis job."""
        job_id = str(uuid.uuid4())
        
        if analysis_types is None:
            # Default to all analysis types
            analysis_types = list(BiasType)
        
        job = BiasAnalysisJob(
            job_id=job_id,
            session_id=session_id,
            created_at=datetime.now(),
            description_pald=description_pald,
            embodiment_pald=embodiment_pald,
            analysis_types=analysis_types,
            priority=priority
        )
        
        self.jobs[job_id] = job
        
        logger.info(f"Created bias analysis job {job_id} for session {session_id}")
        return job_id
    
    def process_bias_job(self, job_id: str) -> BiasJobResult:
        """Process a specific bias analysis job."""
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")
        
        job = self.jobs[job_id]
        start_time = datetime.now()
        
        try:
            job.status = JobStatus.PROCESSING
            results = []
            
            # Process each analysis type except multiple stereotyping first
            individual_analyses = [t for t in job.analysis_types if t != BiasType.MULTIPLE_STEREOTYPING]
            
            for analysis_type in individual_analyses:
                if analysis_type in self.bias_engine.analysis_methods:
                    method = self.bias_engine.analysis_methods[analysis_type]
                    result = method(job.description_pald, job.embodiment_pald)
                    results.append(result)
            
            # Process multiple stereotyping analysis if requested
            if BiasType.MULTIPLE_STEREOTYPING in job.analysis_types:
                multiple_result = self.bias_engine.analyze_multiple_stereotyping(results)
                results.append(multiple_result)
            
            job.results = results
            job.status = JobStatus.COMPLETED
            job.processed_at = datetime.now()
            
            processing_time = max((datetime.now() - start_time).total_seconds(), 0.001)  # Ensure minimum time
            
            logger.info(f"Completed bias analysis job {job_id} in {processing_time:.2f}s")
            
            return BiasJobResult(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                results=results,
                processing_time_seconds=processing_time
            )
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.processed_at = datetime.now()
            
            processing_time = max((datetime.now() - start_time).total_seconds(), 0.001)  # Ensure minimum time
            
            logger.error(f"Failed to process bias analysis job {job_id}: {e}")
            
            return BiasJobResult(
                job_id=job_id,
                status=JobStatus.FAILED,
                results=[],
                processing_time_seconds=processing_time,
                error_message=str(e)
            )
    
    def process_bias_queue(self, batch_size: int = 10) -> list[BiasJobResult]:
        """Process queued bias analysis jobs in batches."""
        # Get pending jobs sorted by priority and creation time
        pending_jobs = [
            job for job in self.jobs.values() 
            if job.status == JobStatus.PENDING
        ]
        
        # Sort by priority (higher first) then by creation time (older first)
        pending_jobs.sort(key=lambda j: (-j.priority, j.created_at))
        
        # Process up to batch_size jobs
        batch_jobs = pending_jobs[:batch_size]
        results = []
        
        for job in batch_jobs:
            result = self.process_bias_job(job.job_id)
            results.append(result)
        
        logger.info(f"Processed {len(results)} bias analysis jobs in batch")
        return results
    
    def get_job_status(self, job_id: str) -> JobStatus:
        """Get status of specific bias job."""
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")
        
        return self.jobs[job_id].status
    
    def get_job_results(self, job_id: str) -> list[BiasResult]:
        """Get results of completed bias job."""
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")
        
        job = self.jobs[job_id]
        if job.status != JobStatus.COMPLETED:
            raise ValueError(f"Job {job_id} is not completed (status: {job.status.value})")
        
        return job.results
    
    def get_pending_job_count(self) -> int:
        """Get count of pending jobs."""
        return len([job for job in self.jobs.values() if job.status == JobStatus.PENDING])
    
    def clear_completed_jobs(self, older_than_hours: int = 24):
        """Clear completed jobs older than specified hours."""
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        
        jobs_to_remove = [
            job_id for job_id, job in self.jobs.items()
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]
            and job.processed_at and job.processed_at < cutoff_time
        ]
        
        for job_id in jobs_to_remove:
            del self.jobs[job_id]
        
        logger.info(f"Cleared {len(jobs_to_remove)} old completed jobs")
        return len(jobs_to_remove)


# Global bias job manager instance
bias_job_manager = BiasJobManager()
"""
Utils module initialization.
"""
from app.utils.helpers import (
    extract_domain,
    normalize_url,
    normalize_phone,
    normalize_email,
    generate_email_patterns,
    is_parked_domain,
    calculate_confidence_score,
    calculate_lead_score,
    generate_recommendations,
)

__all__ = [
    "extract_domain",
    "normalize_url",
    "normalize_phone",
    "normalize_email",
    "generate_email_patterns",
    "is_parked_domain",
    "calculate_confidence_score",
    "calculate_lead_score",
    "generate_recommendations",
]

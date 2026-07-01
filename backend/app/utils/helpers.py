"""
Utility functions for the LeadGen AI Platform.
"""
import re
import tldextract
from typing import Optional, List, Tuple
from urllib.parse import urlparse
import phonenumbers
from phonenumbers import PhoneNumberFormat, NumberParseException


def extract_domain(url: str) -> Optional[str]:
    """Extract domain from URL."""
    if not url:
        return None
    
    # Add scheme if missing
    if not url.startswith(('http://', 'https://')):
        url = f'https://{url}'
    
    try:
        extracted = tldextract.extract(url)
        if extracted.domain and extracted.suffix:
            return f"{extracted.domain}.{extracted.suffix}"
    except Exception:
        pass
    
    return None


def normalize_url(url: str) -> Optional[str]:
    """Normalize URL to standard format."""
    if not url:
        return None
    
    url = url.strip()
    
    # Add scheme if missing
    if not url.startswith(('http://', 'https://')):
        url = f'https://{url}'
    
    try:
        parsed = urlparse(url)
        if parsed.netloc:
            return parsed.geturl()
    except Exception:
        pass
    
    return None


def normalize_phone(phone: str, country_code: str = "US") -> Optional[str]:
    """Normalize phone number to E.164 format."""
    if not phone:
        return None
    
    # Remove common separators
    phone = re.sub(r'[\s\-\.\(\)]', '', phone)
    
    try:
        parsed = phonenumbers.parse(phone, country_code)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
    except NumberParseException:
        pass
    
    return None


def normalize_email(email: str) -> Optional[str]:
    """Normalize email address."""
    if not email:
        return None
    
    email = email.strip().lower()
    
    # Basic email validation
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        return email
    
    return None


def generate_email_patterns(domain: str, first_name: Optional[str] = None, last_name: Optional[str] = None) -> List[str]:
    """Generate likely email patterns for a domain."""
    if not domain:
        return []
    
    patterns = [
        f"info@{domain}",
        f"contact@{domain}",
        f"sales@{domain}",
        f"support@{domain}",
        f"office@{domain}",
        f"admin@{domain}",
        f"hello@{domain}",
    ]
    
    if first_name and last_name:
        first = first_name.lower().strip()
        last = last_name.lower().strip()
        
        patterns.extend([
            f"{first}@{domain}",
            f"{last}@{domain}",
            f"{first}{last}@{domain}",
            f"{first}.{last}@{domain}",
            f"{first}_{last}@{domain}",
            f"{first[0]}{last}@{domain}",
            f"{first}{last[0]}@{domain}",
            f"{first[0]}.{last}@{domain}",
        ])
    elif first_name:
        first = first_name.lower().strip()
        patterns.append(f"{first}@{domain}")
    
    return patterns


def is_parked_domain(domain: str) -> bool:
    """Check if domain appears to be parked."""
    parked_indicators = [
        "parked",
        "for sale",
        "this domain is for sale",
        "buy this domain",
        "domain parked",
        "placeholder",
        "coming soon",
    ]
    
    # This would need actual website content to check properly
    # For now, return False - actual implementation in service layer
    return False


def calculate_confidence_score(source: str) -> int:
    """Calculate confidence score based on data source."""
    source_scores = {
        "official_website": 100,
        "official_contact_page": 95,
        "google_business": 90,
        "linkedin": 85,
        "facebook": 80,
        "yellow_pages": 75,
        "government_registry": 70,
        "business_directory": 60,
        "ai_estimated": 50,
    }
    
    return source_scores.get(source.lower(), 50)


def calculate_lead_score(lead_data: dict) -> Tuple[int, str]:
    """
    Calculate lead score (0-100) and quality (hot/warm/cold).
    
    Criteria:
    - Website exists: +10
    - Business email found: +20
    - LinkedIn found: +10
    - Facebook found: +5
    - Phone found: +10
    - Complete address: +5
    - Multiple emails: +10
    - Social media presence: +10
    - Industry identified: +5
    - Employee count known: +5
    - Revenue estimate known: +5
    - Recent activity: +5
    """
    score = 0
    
    if lead_data.get('website'):
        score += 10
    
    if lead_data.get('primary_email'):
        score += 20
    
    if lead_data.get('secondary_email') or lead_data.get('sales_email'):
        score += 10
    
    if lead_data.get('linkedin_url'):
        score += 10
    
    if lead_data.get('facebook_url'):
        score += 5
    
    if lead_data.get('phone'):
        score += 10
    
    if lead_data.get('address') and lead_data.get('city') and lead_data.get('state'):
        score += 5
    
    social_count = sum([
        1 if lead_data.get('linkedin_url') else 0,
        1 if lead_data.get('facebook_url') else 0,
        1 if lead_data.get('instagram_url') else 0,
        1 if lead_data.get('twitter_url') else 0,
    ])
    score += min(social_count * 3, 10)
    
    if lead_data.get('industry') or lead_data.get('category'):
        score += 5
    
    if lead_data.get('estimated_employees'):
        score += 5
    
    if lead_data.get('estimated_revenue'):
        score += 5
    
    # Cap at 100
    score = min(score, 100)
    
    # Determine quality
    if score >= 70:
        quality = "hot"
    elif score >= 40:
        quality = "warm"
    else:
        quality = "cold"
    
    return score, quality


def generate_recommendations(lead_data: dict) -> List[str]:
    """Generate service recommendations based on lead data."""
    recommendations = []
    
    # Website recommendations
    if lead_data.get('website'):
        if not lead_data.get('https_enabled'):
            recommendations.append("SSL Installation")
        
        if lead_data.get('page_speed_score') and lead_data['page_speed_score'] < 70:
            recommendations.append("Website Speed Optimization")
        
        if not lead_data.get('mobile_friendly'):
            recommendations.append("Mobile Optimization")
        
        if lead_data.get('seo_score') and lead_data['seo_score'] < 60:
            recommendations.append("SEO Improvement")
        
        if not lead_data.get('schema_markup_detected'):
            recommendations.append("Schema Markup Implementation")
    
    else:
        recommendations.append("Website Development")
    
    # Online presence
    if not lead_data.get('linkedin_url'):
        recommendations.append("LinkedIn Profile Setup")
    
    if not lead_data.get('facebook_url'):
        recommendations.append("Facebook Business Page")
    
    if not lead_data.get('google_analytics_detected') and lead_data.get('website'):
        recommendations.append("Google Analytics Setup")
    
    # Marketing
    if not lead_data.get('primary_email'):
        recommendations.append("Professional Email Setup")
    
    recommendations.append("Local SEO Optimization")
    recommendations.append("Google Business Profile Optimization")
    
    return list(set(recommendations))[:5]  # Return top 5 unique recommendations

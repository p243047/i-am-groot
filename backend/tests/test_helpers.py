"""
Tests for utility helper functions.
"""
import pytest
from app.utils.helpers import (
    extract_domain,
    normalize_url,
    normalize_phone,
    normalize_email,
    generate_email_patterns,
    calculate_confidence_score,
    calculate_lead_score,
    generate_recommendations,
)


class TestExtractDomain:
    """Tests for extract_domain function."""
    
    def test_extract_domain_with_https(self):
        assert extract_domain("https://www.example.com") == "example.com"
    
    def test_extract_domain_with_http(self):
        assert extract_domain("http://example.com") == "example.com"
    
    def test_extract_domain_without_scheme(self):
        assert extract_domain("example.com") == "example.com"
    
    def test_extract_domain_with_path(self):
        assert extract_domain("https://example.com/page/subpage") == "example.com"
    
    def test_extract_domain_subdomain(self):
        assert extract_domain("https://sub.example.co.uk") == "example.co.uk"
    
    def test_extract_domain_none(self):
        assert extract_domain("") is None
        assert extract_domain(None) is None


class TestNormalizeUrl:
    """Tests for normalize_url function."""
    
    def test_normalize_url_adds_https(self):
        result = normalize_url("example.com")
        assert result.startswith("https://")
    
    def test_normalize_url_preserves_https(self):
        result = normalize_url("https://example.com")
        assert result.startswith("https://")
    
    def test_normalize_url_none(self):
        assert normalize_url("") is None
        assert normalize_url(None) is None


class TestNormalizePhone:
    """Tests for normalize_phone function."""
    
    def test_normalize_us_phone(self):
        result = normalize_phone("(555) 123-4567", "US")
        assert result == "+15551234567"
    
    def test_normalize_phone_with_spaces(self):
        result = normalize_phone("555 123 4567", "US")
        assert result == "+15551234567"
    
    def test_normalize_phone_none(self):
        assert normalize_phone("", "US") is None
        assert normalize_phone(None, "US") is None


class TestNormalizeEmail:
    """Tests for normalize_email function."""
    
    def test_normalize_valid_email(self):
        assert normalize_email("test@example.com") == "test@example.com"
    
    def test_normalize_email_lowercase(self):
        assert normalize_email("TEST@EXAMPLE.COM") == "test@example.com"
    
    def test_normalize_invalid_email(self):
        assert normalize_email("invalid-email") is None
        assert normalize_email("") is None
        assert normalize_email(None) is None


class TestGenerateEmailPatterns:
    """Tests for generate_email_patterns function."""
    
    def test_generate_common_patterns(self):
        patterns = generate_email_patterns("example.com")
        assert "info@example.com" in patterns
        assert "contact@example.com" in patterns
        assert "sales@example.com" in patterns
    
    def test_generate_with_name(self):
        patterns = generate_email_patterns("example.com", "john", "doe")
        assert "john.doe@example.com" in patterns
        assert "johndoe@example.com" in patterns
        assert "jdoe@example.com" in patterns
    
    def test_generate_empty_domain(self):
        assert generate_email_patterns("") == []


class TestCalculateConfidenceScore:
    """Tests for calculate_confidence_score function."""
    
    def test_official_website_score(self):
        assert calculate_confidence_score("official_website") == 100
    
    def test_linkedin_score(self):
        assert calculate_confidence_score("linkedin") == 85
    
    def test_unknown_source_score(self):
        assert calculate_confidence_score("unknown") == 50


class TestCalculateLeadScore:
    """Tests for calculate_lead_score function."""
    
    def test_high_score_lead(self):
        lead_data = {
            'website': 'https://example.com',
            'primary_email': 'info@example.com',
            'linkedin_url': 'https://linkedin.com/company/example',
            'facebook_url': 'https://facebook.com/example',
            'phone': '+15551234567',
            'address': '123 Main St',
            'city': 'New York',
            'state': 'NY',
            'industry': 'Technology',
            'estimated_employees': '50-100',
            'estimated_revenue': '$1M-$5M',
        }
        score, quality = calculate_lead_score(lead_data)
        assert score > 50
        assert quality in ['hot', 'warm', 'cold']
    
    def test_low_score_lead(self):
        lead_data = {}
        score, quality = calculate_lead_score(lead_data)
        assert score == 0
        assert quality == 'cold'


class TestGenerateRecommendations:
    """Tests for generate_recommendations function."""
    
    def test_recommendations_for_no_website(self):
        recommendations = generate_recommendations({})
        assert 'Website Development' in recommendations
    
    def test_recommendations_for_existing_website(self):
        lead_data = {
            'website': 'https://example.com',
            'https_enabled': False,
            'page_speed_score': 50,
            'mobile_friendly': False,
            'seo_score': 40,
            'schema_markup_detected': False,
            'google_analytics_detected': False,
        }
        recommendations = generate_recommendations(lead_data)
        assert 'SSL Installation' in recommendations
        assert len(recommendations) <= 5

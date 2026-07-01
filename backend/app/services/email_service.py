"""
Email discovery and verification service.
"""
import re
import dns.resolver
from typing import Optional, List, Dict, Any
from email_validator import validate_email, EmailNotValidError
import httpx
from bs4 import BeautifulSoup
from app.utils.helpers import generate_email_patterns, normalize_email


class EmailVerifier:
    """Service for verifying email addresses."""
    
    # Common disposable email domains
    DISPOSABLE_DOMAINS = {
        'tempmail.com', 'throwaway.com', 'guerrillamail.com', 
        'mailinator.com', '10minutemail.com', 'fakeinbox.com'
    }
    
    # Role-based email prefixes
    ROLE_PREFIXES = {
        'info', 'contact', 'support', 'sales', 'admin', 'office',
        'hello', 'help', 'service', 'billing', 'hr', 'jobs',
        'marketing', 'press', 'media', 'legal', 'privacy'
    }
    
    async def verify_email(self, email: str) -> Dict[str, Any]:
        """
        Verify an email address.
        
        Returns:
            dict with status, risk_score, is_disposable, is_role_account, etc.
        """
        result = {
            'email': email,
            'status': 'unknown',
            'risk_score': 50,
            'is_valid_syntax': False,
            'is_disposable': False,
            'is_role_account': False,
            'has_mx_record': False,
            'smtp_check': 'not_checked',
            'is_catch_all': False,
        }
        
        # Step 1: Syntax validation
        try:
            valid = validate_email(email)
            result['is_valid_syntax'] = True
            result['email'] = valid.email  # Normalized email
            email = valid.email
        except EmailNotValidError as e:
            result['status'] = 'invalid'
            result['risk_score'] = 100
            return result
        
        # Step 2: Check disposable domain
        domain = email.split('@')[1]
        if domain.lower() in self.DISPOSABLE_DOMAINS:
            result['is_disposable'] = True
            result['status'] = 'risky'
            result['risk_score'] = 80
            return result
        
        # Step 3: Check role account
        local_part = email.split('@')[0].lower()
        if any(local_part.startswith(prefix) or local_part == prefix 
               for prefix in self.ROLE_PREFIXES):
            result['is_role_account'] = True
            result['risk_score'] = 30  # Lower risk but still valid
        
        # Step 4: MX Record check
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            if mx_records:
                result['has_mx_record'] = True
        except Exception:
            result['status'] = 'invalid'
            result['risk_score'] = 90
            return result
        
        # Step 5: SMTP check (basic - without sending actual email)
        # Note: Full SMTP verification requires actual connection which may be slow
        # This is a simplified check
        result['smtp_check'] = 'likely_valid' if result['has_mx_record'] else 'unknown'
        
        # Calculate final status and risk score
        if result['is_disposable']:
            result['status'] = 'risky'
        elif result['is_role_account'] and result['has_mx_record']:
            result['status'] = 'likely_valid'
            result['risk_score'] = 30
        elif result['has_mx_record']:
            result['status'] = 'verified'
            result['risk_score'] = 10
        else:
            result['status'] = 'unknown'
            result['risk_score'] = 60
        
        return result
    
    async def check_catch_all(self, domain: str) -> bool:
        """Check if domain accepts all emails (catch-all)."""
        # Generate a random test email
        import random
        import string
        test_email = f"{''.join(random.choices(string.ascii_lowercase, k=12))}@{domain}"
        
        try:
            # Try to verify the random email
            mx_records = dns.resolver.resolve(domain, 'MX')
            if not mx_records:
                return False
            
            # Basic catch-all detection - would need actual SMTP for accurate check
            # For now, assume not catch-all
            return False
        except Exception:
            return False


class EmailDiscoveryService:
    """Service for discovering email addresses from various sources."""
    
    def __init__(self):
        self.verifier = EmailVerifier()
        self.timeout = httpx.Timeout(30.0)
    
    async def extract_emails_from_html(self, html: str) -> List[str]:
        """Extract all email addresses from HTML content."""
        emails = set()
        
        # Pattern for email extraction
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        
        # Find all emails in text
        found = re.findall(email_pattern, html)
        for email in found:
            normalized = normalize_email(email)
            if normalized:
                emails.add(normalized)
        
        # Also check in href attributes (mailto links)
        soup = BeautifulSoup(html, 'lxml')
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('mailto:'):
                email = href.replace('mailto:', '').split('?')[0].strip()
                normalized = normalize_email(email)
                if normalized:
                    emails.add(normalized)
        
        return list(emails)
    
    async def scrape_website_emails(self, url: str) -> List[Dict[str, Any]]:
        """
        Scrape email addresses from a website.
        
        Searches:
        - Homepage
        - Contact page
        - About page
        - Footer
        - Team/Staff pages
        """
        results = []
        base_domain = url.rstrip('/')
        
        pages_to_check = [
            '/',
            '/contact',
            '/contact-us',
            '/about',
            '/about-us',
            '/team',
            '/staff',
            '/leadership',
            '/careers',
            '/jobs',
        ]
        
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for page in pages_to_check:
                try:
                    full_url = f"{base_domain}{page}"
                    response = await client.get(full_url)
                    
                    if response.status_code == 200:
                        emails = await self.extract_emails_from_html(response.text)
                        
                        for email in emails:
                            # Verify each email
                            verification = await self.verifier.verify_email(email)
                            
                            results.append({
                                'email': email,
                                'source': f'website_{page.strip("/") or "home"}',
                                'verification': verification,
                                'url_found': full_url,
                            })
                except Exception:
                    continue
        
        return results
    
    async def search_google_for_emails(self, business_name: str, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search Google for email addresses related to the business."""
        # This would use Google Custom Search API if configured
        # For now, return empty list - actual implementation requires API key
        results = []
        
        # Placeholder for Google CSE integration
        # queries = [
        #     f'{business_name} email contact',
        #     f'{business_name} "@{domain}"' if domain else '',
        #     f'site:{domain} email contact' if domain else '',
        # ]
        
        return results
    
    async def generate_and_verify_emails(
        self,
        domain: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        max_attempts: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Generate likely email patterns and verify them.
        
        Only generates emails for known company domains.
        """
        results = []
        
        # Generate patterns
        patterns = generate_email_patterns(domain, first_name, last_name)
        
        # Limit attempts
        patterns = patterns[:max_attempts]
        
        # Verify each generated email
        for email in patterns:
            verification = await self.verifier.verify_email(email)
            
            # Only include potentially valid emails
            if verification['status'] in ['verified', 'likely_valid', 'catch_all']:
                results.append({
                    'email': email,
                    'source': 'generated_pattern',
                    'verification': verification,
                    'is_generated': True,
                })
        
        return results
    
    async def discover_primary_email(
        self,
        business_name: str,
        domain: Optional[str],
        website_url: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Main method to discover primary business email.
        
        Strategy:
        1. Scrape website if available
        2. Search public sources
        3. Generate patterns if domain known
        """
        all_emails = []
        
        # Stage 1: Website scraping
        if website_url:
            website_emails = await self.scrape_website_emails(website_url)
            all_emails.extend(website_emails)
        
        # Stage 2: Public source search (requires API keys)
        # google_emails = await self.search_google_for_emails(business_name, domain)
        # all_emails.extend(google_emails)
        
        # Stage 3: Generate patterns if domain known
        if domain:
            generated = await self.generate_and_verify_emails(domain)
            all_emails.extend(generated)
        
        if not all_emails:
            return None
        
        # Sort by confidence (verified first, then role accounts)
        all_emails.sort(key=lambda x: (
            0 if x['verification']['status'] == 'verified' else 1,
            0 if not x['verification']['is_role_account'] else 1,
            x['verification']['risk_score'],
        ))
        
        # Return best email
        return all_emails[0] if all_emails else None

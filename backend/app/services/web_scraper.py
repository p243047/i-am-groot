"""
Web scraping service for business information enrichment.
"""
import asyncio
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, urljoin
import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from app.core.config import get_settings
from app.utils.helpers import extract_domain, normalize_url

settings = get_settings()


class WebScraperService:
    """Service for scraping business information from websites."""
    
    def __init__(self):
        self.timeout = httpx.Timeout(30.0)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    
    async def fetch_with_httpx(self, url: str) -> Optional[str]:
        """Fetch webpage content using httpx."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(url, follow_redirects=True)
                if response.status_code == 200:
                    return response.text
        except Exception:
            pass
        return None
    
    async def fetch_with_playwright(self, url: str) -> Optional[str]:
        """Fetch webpage content using Playwright for JavaScript-rendered pages."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=settings.PLAYWRIGHT_HEADLESS)
                page = await browser.new_page()
                
                await page.goto(url, timeout=settings.PLAYWRIGHT_TIMEOUT)
                await page.wait_for_load_state('networkidle')
                
                content = await page.content()
                await browser.close()
                return content
        except Exception:
            pass
        return None
    
    async def scrape_business_info(self, url: str) -> Dict[str, Any]:
        """
        Scrape business information from a website.
        
        Returns:
            dict with business name, description, phone, address, social links, etc.
        """
        result = {
            'business_name': None,
            'description': None,
            'phone': None,
            'address': None,
            'city': None,
            'state': None,
            'zip_code': None,
            'country': None,
            'social_links': {},
            'technologies': [],
            'meta_description': None,
            'title': None,
            'logo_url': None,
        }
        
        # Try httpx first, then Playwright if needed
        html = await self.fetch_with_httpx(url)
        if not html or len(html) < 500:  # Very short page might be error
            html = await self.fetch_with_playwright(url)
        
        if not html:
            return result
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Extract title
        title_tag = soup.find('title')
        if title_tag:
            result['title'] = title_tag.get_text(strip=True)[:500]
        
        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            result['meta_description'] = meta_desc['content'].strip()[:1000]
        
        # Extract business name (try multiple selectors)
        business_name_selectors = [
            ('h1', {}),
            ('.logo', {}),
            ('[class*="logo"]', {}),
            ('.company-name', {}),
            ('[itemprop="name"]', {}),
        ]
        
        for selector, attrs in business_name_selectors:
            element = soup.find(selector, attrs) if attrs else soup.find(selector)
            if element and element.get_text(strip=True):
                name = element.get_text(strip=True)
                if len(name) < 200:  # Reasonable length
                    result['business_name'] = name
                    break
        
        # If no business name found, use title
        if not result['business_name'] and result['title']:
            result['business_name'] = result['title'].split('|')[0].strip()
        
        # Extract phone numbers
        phone_patterns = [
            r'\+?1?\s*\(?[0-9]{3}\)?[\s.-]?[0-9]{3}[\s.-]?[0-9]{4}',
            r'\+?[0-9]{1,3}[\s.-]?[0-9]{2,4}[\s.-]?[0-9]{3,4}[\s.-]?[0-9]{3,4}',
        ]
        
        import re
        for pattern in phone_patterns:
            phones = re.findall(pattern, html)
            if phones:
                result['phone'] = phones[0]
                break
        
        # Extract address (look for structured data first)
        address_element = soup.find(attrs={'itemprop': 'address'})
        if address_element:
            result['address'] = address_element.get_text(strip=True)[:500]
        
        # Look for common address patterns
        address_selectors = ['.address', '[class*="address"]', '.location', '.contact-address']
        for selector in address_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if len(text) > 10 and len(text) < 300:
                    result['address'] = text
                    break
        
        # Extract social media links
        social_patterns = {
            'linkedin': r'linkedin\.com/company/[^"\'>\s]+|linkedin\.com/in/[^"\'>\s]+',
            'facebook': r'facebook\.com/[^"\'>\s]+',
            'instagram': r'instagram\.com/[^"\'>\s]+',
            'twitter': r'twitter\.com/[^"\'>\s]+|x\.com/[^"\'>\s]+',
            'youtube': r'youtube\.com/[^"\'>\s]+',
            'pinterest': r'pinterest\.com/[^"\'>\s]+',
        }
        
        for platform, pattern in social_patterns.items():
            import re
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                link = matches[0]
                if not link.startswith('http'):
                    link = f'https://{link}'
                result['social_links'][platform] = link
        
        # Also check footer and navigation for social links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if 'linkedin.com' in href.lower():
                result['social_links']['linkedin'] = href
            elif 'facebook.com' in href.lower():
                result['social_links']['facebook'] = href
            elif 'instagram.com' in href.lower():
                result['social_links']['instagram'] = href
            elif 'twitter.com' in href.lower() or 'x.com' in href.lower():
                result['social_links']['twitter'] = href
        
        # Detect technologies (basic detection)
        result['technologies'] = self._detect_technologies(html, soup)
        
        # Try to find logo
        logo_selectors = ['.logo img', '[class*="logo"] img', '.header img[src*="logo"]']
        for selector in logo_selectors:
            img = soup.select_one(selector)
            if img and img.get('src'):
                logo_src = img['src']
                if not logo_src.startswith('http'):
                    parsed = urlparse(url)
                    logo_src = urljoin(f'{parsed.scheme}://{parsed.netloc}', logo_src)
                result['logo_url'] = logo_src
                break
        
        return result
    
    def _detect_technologies(self, html: str, soup: BeautifulSoup) -> List[str]:
        """Detect website technologies."""
        technologies = []
        
        # Check for common CMS signatures
        cms_indicators = {
            'WordPress': ['wp-content', 'wp-includes', 'wp-json'],
            'Shopify': ['shopify', 'cdn.shopify.com'],
            'Squarespace': ['squarespace', 'static.squarespace.com'],
            'Wix': ['wix.com', 'wixsite.com', 'static.wixstatic.com'],
            'Joomla': ['joomla', '/media/jui/'],
            'Drupal': ['drupal', '/sites/default/files/'],
            'Magento': ['mage-', 'varien'],
        }
        
        for cms, indicators in cms_indicators.items():
            if any(indicator in html.lower() for indicator in indicators):
                technologies.append(cms)
        
        # Check for analytics
        if 'google-analytics' in html.lower() or 'gtag.js' in html.lower():
            technologies.append('Google Analytics')
        
        if 'facebook-pixel' in html.lower() or 'fbq' in html.lower():
            technologies.append('Facebook Pixel')
        
        # Check for schema markup
        if soup.find('script', type='application/ld+json'):
            technologies.append('Schema.org')
        
        # Check for common frameworks
        framework_indicators = {
            'React': ['react', 'react-dom'],
            'Vue.js': ['vue.js', 'vuejs'],
            'Angular': ['angular', 'ng-'],
            'jQuery': ['jquery'],
            'Bootstrap': ['bootstrap', 'bootstrapcdn'],
            'Tailwind CSS': ['tailwind'],
        }
        
        for framework, indicators in framework_indicators.items():
            scripts = soup.find_all('script', src=True)
            for script in scripts:
                src = script.get('src', '').lower()
                if any(indicator in src for indicator in indicators):
                    technologies.append(framework)
                    break
        
        return list(set(technologies))
    
    async def check_https_ssl(self, url: str) -> Dict[str, bool]:
        """Check if website has HTTPS and valid SSL."""
        result = {
            'https_enabled': False,
            'ssl_valid': False,
        }
        
        try:
            parsed = urlparse(url)
            if parsed.scheme == 'https':
                result['https_enabled'] = True
                
                # Try to connect and verify SSL
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url)
                    # If we got here without exception, SSL is valid
                    result['ssl_valid'] = True
        except httpx.SSLVerificationError:
            result['https_enabled'] = True
            result['ssl_valid'] = False
        except Exception:
            pass
        
        return result
    
    async def get_website_metadata(self, url: str) -> Dict[str, Any]:
        """Get comprehensive website metadata."""
        result = {
            'url': url,
            'domain': extract_domain(url),
            'title': None,
            'meta_description': None,
            'keywords': [],
            'og_tags': {},
            'twitter_cards': {},
            'canonical_url': None,
            'robots_meta': None,
        }
        
        html = await self.fetch_with_httpx(url)
        if not html:
            return result
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Title
        title_tag = soup.find('title')
        if title_tag:
            result['title'] = title_tag.get_text(strip=True)
        
        # Meta description
        desc = soup.find('meta', attrs={'name': 'description'})
        if desc and desc.get('content'):
            result['meta_description'] = desc['content'].strip()
        
        # Keywords
        keywords = soup.find('meta', attrs={'name': 'keywords'})
        if keywords and keywords.get('content'):
            result['keywords'] = [k.strip() for k in keywords['content'].split(',')]
        
        # Open Graph tags
        og_prefix = {'property': lambda v: v.startswith('og:')}
        for meta in soup.find_all('meta', property=lambda v: v and v.startswith('og:')):
            prop = meta.get('property', '')
            content = meta.get('content', '')
            if prop and content:
                result['og_tags'][prop.replace('og:', '')] = content
        
        # Twitter Card tags
        for meta in soup.find_all('meta', attrs={'name': lambda v: v and v.startswith('twitter:')}):
            name = meta.get('name', '')
            content = meta.get('content', '')
            if name and content:
                result['twitter_cards'][name.replace('twitter:', '')] = content
        
        # Canonical URL
        canonical = soup.find('link', rel='canonical')
        if canonical and canonical.get('href'):
            result['canonical_url'] = canonical['href']
        
        # Robots meta
        robots = soup.find('meta', attrs={'name': 'robots'})
        if robots and robots.get('content'):
            result['robots_meta'] = robots['content']
        
        return result

"""
Business enrichment service - orchestrates all data collection.
"""
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.schemas import Lead, LeadStatus, ProcessingLog, EmailVerificationStatus
from app.services.email_service import EmailDiscoveryService, EmailVerifier
from app.services.web_scraper import WebScraperService
from app.utils.helpers import (
    extract_domain,
    normalize_url,
    normalize_phone,
    calculate_confidence_score,
    calculate_lead_score,
    generate_recommendations,
)


class BusinessEnrichmentService:
    """
    Main service for enriching business lead data.
    
    Orchestrates:
    - Website scraping
    - Email discovery
    - Social media lookup
    - Technology detection
    - Lead scoring
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.web_scraper = WebScraperService()
        self.email_discovery = EmailDiscoveryService()
        self.email_verifier = EmailVerifier()
    
    async def log_action(
        self,
        batch_id: int,
        lead_id: Optional[int],
        action: str,
        source: Optional[str],
        status: str,
        message: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        """Log a processing action."""
        log = ProcessingLog(
            batch_id=batch_id,
            lead_id=lead_id,
            action=action,
            source=source,
            status=status,
            message=message,
            metadata=metadata or {},
        )
        self.db.add(log)
        await self.db.flush()
    
    async def enrich_lead(self, lead: Lead) -> Lead:
        """
        Enrich a single lead with all available data.
        
        Strategy:
        1. Extract/normalize domain from website
        2. Scrape website for business info
        3. Discover emails
        4. Look up social media profiles
        5. Calculate scores and recommendations
        """
        sources_used = []
        errors = []
        
        try:
            # Update status to enriching
            lead.status = LeadStatus.ENRICHING
            await self.db.flush()
            
            # Get website URL from original data if not set
            if not lead.website:
                lead.website = lead.original_data.get('website') or lead.original_data.get('Website')
            
            if not lead.business_name:
                lead.business_name = lead.original_data.get('business_name') or lead.original_data.get('Business Name')
            
            if not lead.phone:
                lead.phone = lead.original_data.get('phone') or lead.original_data.get('Phone')
            
            if not lead.address:
                lead.address = lead.original_data.get('address') or lead.original_data.get('Address')
            
            # Normalize website and extract domain
            if lead.website:
                lead.website = normalize_url(lead.website)
                if lead.website:
                    lead.domain = extract_domain(lead.website)
                    
                    if lead.domain:
                        sources_used.append('official_website')
                        
                        # Scrape website for business info
                        await self.log_action(
                            batch_id=lead.batch_id,
                            lead_id=lead.id,
                            action='scrape_website',
                            source='official_website',
                            status='started',
                            message=f'Scraping {lead.website}',
                        )
                        
                        try:
                            web_info = await self.web_scraper.scrape_business_info(lead.website)
                            
                            # Merge scraped data
                            if web_info.get('business_name') and not lead.business_name:
                                lead.business_name = web_info['business_name']
                            
                            if web_info.get('phone') and not lead.phone:
                                lead.phone = web_info['phone']
                            
                            if web_info.get('address') and not lead.address:
                                lead.address = web_info['address']
                            
                            if web_info.get('social_links'):
                                if web_info['social_links'].get('linkedin') and not lead.linkedin_url:
                                    lead.linkedin_url = web_info['social_links']['linkedin']
                                if web_info['social_links'].get('facebook') and not lead.facebook_url:
                                    lead.facebook_url = web_info['social_links']['facebook']
                                if web_info['social_links'].get('instagram') and not lead.instagram_url:
                                    lead.instagram_url = web_info['social_links']['instagram']
                                if web_info['social_links'].get('twitter') and not lead.twitter_url:
                                    lead.twitter_url = web_info['social_links']['twitter']
                            
                            if web_info.get('technologies'):
                                lead.website_technologies = web_info['technologies']
                            
                            if web_info.get('meta_description'):
                                lead.meta_description = web_info['meta_description']
                            
                            if web_info.get('title'):
                                lead.title_tag = web_info['title']
                            
                            if web_info.get('logo_url'):
                                lead.logo_url = web_info['logo_url']
                            
                            await self.log_action(
                                batch_id=lead.batch_id,
                                lead_id=lead.id,
                                action='scrape_website',
                                source='official_website',
                                status='success',
                                message=f'Scraped {len(web_info)} data points',
                                metadata={'data_points': len([v for v in web_info.values() if v])},
                            )
                        except Exception as e:
                            errors.append(f'Website scrape error: {str(e)}')
                            await self.log_action(
                                batch_id=lead.batch_id,
                                lead_id=lead.id,
                                action='scrape_website',
                                source='official_website',
                                status='error',
                                message=str(e),
                            )
                        
                        # Check HTTPS/SSL
                        try:
                            ssl_info = await self.web_scraper.check_https_ssl(lead.website)
                            lead.https_enabled = ssl_info['https_enabled']
                            lead.ssl_valid = ssl_info['ssl_valid']
                        except Exception:
                            pass
            
            # Email discovery
            if lead.domain:
                await self.log_action(
                    batch_id=lead.batch_id,
                    lead_id=lead.id,
                    action='discover_email',
                    source='email_discovery',
                    status='started',
                    message=f'Discovering emails for {lead.domain}',
                )
                
                try:
                    email_result = await self.email_discovery.discover_primary_email(
                        business_name=lead.business_name or '',
                        domain=lead.domain,
                        website_url=lead.website,
                    )
                    
                    if email_result:
                        lead.primary_email = email_result['email']
                        lead.email_source = email_result.get('source', 'unknown')
                        
                        verification = email_result.get('verification', {})
                        if verification.get('status') == 'verified':
                            lead.email_verification_status = EmailVerificationStatus.VERIFIED
                        elif verification.get('status') == 'likely_valid':
                            lead.email_verification_status = EmailVerificationStatus.LIKELY_VALID
                        elif verification.get('is_catch_all'):
                            lead.email_verification_status = EmailVerificationStatus.CATCH_ALL
                        elif verification.get('risk_score', 100) > 70:
                            lead.email_verification_status = EmailVerificationStatus.RISKY
                        else:
                            lead.email_verification_status = EmailVerificationStatus.UNKNOWN
                        
                        await self.log_action(
                            batch_id=lead.batch_id,
                            lead_id=lead.id,
                            action='discover_email',
                            source='email_discovery',
                            status='success',
                            message=f'Found email: {lead.primary_email}',
                            metadata={'verification_status': lead.email_verification_status.value if lead.email_verification_status else 'unknown'},
                        )
                    else:
                        await self.log_action(
                            batch_id=lead.batch_id,
                            lead_id=lead.id,
                            action='discover_email',
                            source='email_discovery',
                            status='no_results',
                            message='No valid emails found',
                        )
                except Exception as e:
                    errors.append(f'Email discovery error: {str(e)}')
                    await self.log_action(
                        batch_id=lead.batch_id,
                        lead_id=lead.id,
                        action='discover_email',
                        source='email_discovery',
                        status='error',
                        message=str(e),
                    )
            
            # Normalize phone
            if lead.phone:
                lead.phone = normalize_phone(lead.phone)
            
            # Calculate confidence score based on best source
            if sources_used:
                lead.confidence_score = max(calculate_confidence_score(s) for s in sources_used)
            else:
                lead.confidence_score = 50  # Default for AI estimated
            
            # Prepare data for scoring
            lead_data = {
                'website': lead.website,
                'primary_email': lead.primary_email,
                'secondary_email': lead.secondary_email,
                'sales_email': lead.sales_email,
                'linkedin_url': lead.linkedin_url,
                'facebook_url': lead.facebook_url,
                'instagram_url': lead.instagram_url,
                'twitter_url': lead.twitter_url,
                'phone': lead.phone,
                'address': lead.address,
                'city': lead.city,
                'state': lead.state,
                'industry': lead.industry,
                'category': lead.category,
                'estimated_employees': lead.estimated_employees,
                'estimated_revenue': lead.estimated_revenue,
                'page_speed_score': lead.page_speed_score,
                'mobile_friendly': lead.mobile_friendly,
                'seo_score': lead.seo_score,
                'schema_markup_detected': lead.schema_markup_detected,
                'google_analytics_detected': lead.google_analytics_detected,
            }
            
            # Calculate lead score and quality
            score, quality = calculate_lead_score(lead_data)
            lead.lead_score = score
            lead.lead_quality = quality
            
            # Generate recommendations
            recommendations = generate_recommendations(lead_data)
            lead.recommended_services = recommendations
            
            # Generate AI notes
            ai_notes = []
            if lead.lead_quality == 'hot':
                ai_notes.append('High-quality lead with strong online presence.')
            elif lead.lead_quality == 'warm':
                ai_notes.append('Moderate-quality lead with some contact information.')
            else:
                ai_notes.append('Low-quality lead - limited information available.')
            
            if lead.primary_email:
                ai_notes.append(f'Primary email found: {lead.primary_email}')
            
            if not lead.website:
                ai_notes.append('No website detected - consider outreach via phone/social media.')
            
            lead.ai_notes = ' '.join(ai_notes)
            
            # Set sources used
            lead.sources_used = list(set(sources_used))
            
            # Mark as enriched
            lead.status = LeadStatus.ENRICHED
            lead.enriched_at = datetime.utcnow()
            lead.error_message = '\n'.join(errors) if errors else None
            
        except Exception as e:
            lead.status = LeadStatus.FAILED
            lead.error_message = str(e)
            await self.log_action(
                batch_id=lead.batch_id,
                lead_id=lead.id,
                action='enrich_lead',
                source='orchestrator',
                status='error',
                message=str(e),
            )
        
        return lead

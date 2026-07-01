"""
File processing service for Excel/CSV uploads.
"""
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.schemas import Batch, Lead, ProcessingStatus, LeadStatus, ProcessingLog
from app.core.config import get_settings

settings = get_settings()


class FileProcessingService:
    """Service for processing uploaded Excel/CSV files."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.upload_dir = Path('/app/uploads')
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def process_upload(
        self,
        file_content: bytes,
        filename: str,
        user_id: int,
        batch_name: Optional[str] = None,
    ) -> Batch:
        """
        Process uploaded file and create batch with leads.
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            user_id: ID of uploading user
            batch_name: Optional custom batch name
        
        Returns:
            Created Batch object
        """
        # Generate unique filename
        file_ext = Path(filename).suffix.lower()
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        file_path = self.upload_dir / unique_filename
        
        # Save file
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # Parse file based on extension
        records = await self._parse_file(file_path, file_ext)
        
        # Create batch record
        batch = Batch(
            user_id=user_id,
            name=batch_name or Path(filename).stem,
            original_filename=filename,
            file_path=str(file_path),
            total_records=len(records),
            processed_records=0,
            successful_records=0,
            failed_records=0,
            status=ProcessingStatus.PENDING,
            progress_percentage=0.0,
        )
        
        self.db.add(batch)
        await self.db.flush()  # Get batch ID
        
        # Create lead records
        leads = []
        for idx, record in enumerate(records):
            lead = Lead(
                batch_id=batch.id,
                row_number=idx + 1,
                original_data=self._normalize_record(record),
                status=LeadStatus.NEW,
            )
            
            # Pre-populate known fields
            lead.business_name = record.get('Business Name') or record.get('business_name') or record.get('Company') or record.get('company')
            lead.website = record.get('Website') or record.get('website') or record.get('URL') or record.get('url')
            lead.phone = record.get('Phone') or record.get('phone') or record.get('Phone Number') or record.get('phone_number')
            lead.address = record.get('Address') or record.get('address') or record.get('Street') or record.get('street')
            lead.city = record.get('City') or record.get('city')
            lead.state = record.get('State') or record.get('state') or record.get('Province') or record.get('province')
            lead.zip_code = record.get('ZIP') or record.get('zip') or record.get('Postal Code') or record.get('postal_code')
            lead.country = record.get('Country') or record.get('country')
            
            leads.append(lead)
        
        self.db.add_all(leads)
        
        # Log batch creation
        log = ProcessingLog(
            batch_id=batch.id,
            action='batch_created',
            source='file_upload',
            status='success',
            message=f'Created batch with {len(records)} records',
            metadata={'filename': filename, 'record_count': len(records)},
        )
        self.db.add(log)
        
        await self.db.flush()
        
        return batch
    
    async def _parse_file(self, file_path: Path, file_ext: str) -> List[Dict[str, Any]]:
        """Parse Excel or CSV file into list of records."""
        try:
            if file_ext in ['.xlsx', '.xls']:
                # Read Excel file
                df = pd.read_excel(file_path, engine='openpyxl' if file_ext == '.xlsx' else 'xlrd')
            elif file_ext == '.csv':
                # Read CSV file
                df = pd.read_csv(file_path)
            else:
                raise ValueError(f'Unsupported file type: {file_ext}')
            
            # Convert to list of dicts
            # Replace NaN with None for JSON serialization
            records = df.where(pd.notnull(df), None).to_dict(orient='records')
            
            return records
            
        except Exception as e:
            raise ValueError(f'Failed to parse file: {str(e)}')
    
    def _normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize record keys to consistent format."""
        normalized = {}
        
        # Common key mappings
        key_mappings = {
            'business_name': ['Business Name', 'business_name', 'Company', 'company', 'Business', 'business', 'Name'],
            'website': ['Website', 'website', 'URL', 'url', 'Web Site', 'web_site', 'Domain', 'domain'],
            'phone': ['Phone', 'phone', 'Phone Number', 'phone_number', 'Telephone', 'telephone', 'Mobile', 'mobile'],
            'address': ['Address', 'address', 'Street', 'street', 'Street Address', 'street_address', 'Line 1', 'line_1'],
            'city': ['City', 'city', 'Town', 'town'],
            'state': ['State', 'state', 'Province', 'province', 'Region', 'region'],
            'zip_code': ['ZIP', 'zip', 'Postal Code', 'postal_code', 'Postcode', 'postcode', 'ZIP Code', 'zip_code'],
            'country': ['Country', 'country', 'Nation', 'nation'],
            'email': ['Email', 'email', 'E-mail', 'e_mail', 'Email Address', 'email_address'],
            'industry': ['Industry', 'industry', 'Sector', 'sector', 'Category', 'category'],
        }
        
        for normalized_key, possible_keys in key_mappings.items():
            for key in possible_keys:
                if key in record and record[key] is not None:
                    value = record[key]
                    # Convert pandas types to Python types
                    if pd.isna(value):
                        value = None
                    elif isinstance(value, (pd.Timestamp, datetime)):
                        value = value.isoformat()
                    normalized[normalized_key] = value
                    break
        
        # Include any remaining keys not mapped
        for key, value in record.items():
            if key not in [k for keys in key_mappings.values() for k in keys]:
                if pd.isna(value):
                    value = None
                elif isinstance(value, (pd.Timestamp, datetime)):
                    value = value.isoformat()
                normalized[key] = value
        
        return normalized
    
    async def get_batch_leads(
        self,
        batch_id: int,
        status: Optional[LeadStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Lead]:
        """Get leads for a batch with optional filtering."""
        query = select(Lead).where(Lead.batch_id == batch_id)
        
        if status:
            query = query.where(Lead.status == status)
        
        query = query.offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update_batch_progress(
        self,
        batch_id: int,
        processed: int,
        successful: int,
        failed: int,
    ):
        """Update batch processing progress."""
        batch = await self.db.get(Batch, batch_id)
        if batch:
            batch.processed_records = processed
            batch.successful_records = successful
            batch.failed_records = failed
            
            if batch.total_records > 0:
                batch.progress_percentage = (processed / batch.total_records) * 100
            
            # Auto-complete if all processed
            if processed >= batch.total_records and batch.status == ProcessingStatus.PROCESSING:
                batch.status = ProcessingStatus.COMPLETED
                batch.completed_at = datetime.utcnow()
            
            await self.db.flush()
    
    async def get_pending_leads_count(self, batch_id: int) -> int:
        """Get count of pending leads for a batch."""
        query = select(func.count()).select_from(Lead).where(
            Lead.batch_id == batch_id,
            Lead.status == LeadStatus.NEW,
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

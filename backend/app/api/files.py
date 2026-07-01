"""
File upload and export API endpoints.
"""
import io
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.schemas import Batch, Lead, ProcessingStatus
from app.models.schemas_api import FileUploadResponse, ExportRequest, ExportResponse
from app.services.file_processor import FileProcessingService
from app.api.auth import get_current_user

router = APIRouter()


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    batch_name: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Upload an Excel/CSV file for processing."""
    # Validate file extension
    allowed_extensions = ['xlsx', 'xls', 'csv']
    file_ext = file.filename.split('.')[-1].lower() if file.filename else ''
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}",
        )
    
    # Read file content
    content = await file.read()
    
    # Process file
    processor = FileProcessingService(db)
    batch = await processor.process_upload(
        file_content=content,
        filename=file.filename or "uploaded_file",
        user_id=current_user.id,
        batch_name=batch_name,
    )
    
    return FileUploadResponse(
        batch_id=batch.id,
        filename=batch.original_filename,
        total_records=batch.total_records,
        message=f"File uploaded successfully. {batch.total_records} records found.",
    )


@router.post("/export/{batch_id}")
async def export_batch(
    batch_id: int,
    export_format: str = Form("xlsx"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Export batch results to Excel, CSV, or JSON."""
    # Verify batch ownership
    batch = await db.get(Batch, batch_id)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found",
        )
    
    if batch.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    # Get all leads for this batch
    result = await db.execute(
        select(Lead).where(Lead.batch_id == batch_id).order_by(Lead.row_number)
    )
    leads = list(result.scalars().all())
    
    if not leads:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No leads to export",
        )
    
    # Generate export
    if export_format.lower() == 'json':
        return await _export_json(leads, batch.name)
    elif export_format.lower() == 'csv':
        return await _export_csv(leads, batch.name)
    else:  # xlsx (default)
        return await _export_excel(leads, batch.name)


async def _export_excel(leads: List[Lead], batch_name: str):
    """Export leads to Excel format."""
    import pandas as pd
    
    # Prepare data
    data = []
    for lead in leads:
        row = {
            'Business Name': lead.business_name,
            'Category': lead.category,
            'Industry': lead.industry,
            'Website': lead.website,
            'Domain': lead.domain,
            'Primary Email': lead.primary_email,
            'Secondary Email': lead.secondary_email,
            'Phone': lead.phone,
            'Address': lead.address,
            'City': lead.city,
            'State': lead.state,
            'ZIP': lead.zip_code,
            'Country': lead.country,
            'LinkedIn': lead.linkedin_url,
            'Facebook': lead.facebook_url,
            'Instagram': lead.instagram_url,
            'Employees': lead.estimated_employees,
            'Founded': lead.founded_year,
            'Revenue': lead.estimated_revenue,
            'Lead Score': lead.lead_score,
            'Lead Quality': lead.lead_quality,
            'Confidence': lead.confidence_score,
            'Email Status': lead.email_verification_status.value if lead.email_verification_status else None,
            'Recommendations': ', '.join(lead.recommended_services) if lead.recommended_services else '',
            'AI Notes': lead.ai_notes,
            'Sources': ', '.join(lead.sources_used) if lead.sources_used else '',
            'Status': lead.status.value,
        }
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Write to bytes
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Leads')
    output.seek(0)
    
    filename = f"{batch_name}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


async def _export_csv(leads: List[Lead], batch_name: str):
    """Export leads to CSV format."""
    import pandas as pd
    
    # Prepare data
    data = []
    for lead in leads:
        row = {
            'Business Name': lead.business_name,
            'Category': lead.category,
            'Industry': lead.industry,
            'Website': lead.website,
            'Domain': lead.domain,
            'Primary Email': lead.primary_email,
            'Secondary Email': lead.secondary_email,
            'Phone': lead.phone,
            'Address': lead.address,
            'City': lead.city,
            'State': lead.state,
            'ZIP': lead.zip_code,
            'Country': lead.country,
            'LinkedIn': lead.linkedin_url,
            'Facebook': lead.facebook_url,
            'Instagram': lead.instagram_url,
            'Employees': lead.estimated_employees,
            'Founded': lead.founded_year,
            'Revenue': lead.estimated_revenue,
            'Lead Score': lead.lead_score,
            'Lead Quality': lead.lead_quality,
            'Confidence': lead.confidence_score,
            'Email Status': lead.email_verification_status.value if lead.email_verification_status else None,
            'Recommendations': ', '.join(lead.recommended_services) if lead.recommended_services else '',
            'AI Notes': lead.ai_notes,
            'Sources': ', '.join(lead.sources_used) if lead.sources_used else '',
            'Status': lead.status.value,
        }
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Write to bytes
    output = io.BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    filename = f"{batch_name}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


async def _export_json(leads: List[Lead], batch_name: str):
    """Export leads to JSON format."""
    import json
    
    # Prepare data
    data = []
    for lead in leads:
        row = {
            'business_name': lead.business_name,
            'category': lead.category,
            'industry': lead.industry,
            'website': lead.website,
            'domain': lead.domain,
            'primary_email': lead.primary_email,
            'secondary_email': lead.secondary_email,
            'phone': lead.phone,
            'address': lead.address,
            'city': lead.city,
            'state': lead.state,
            'zip_code': lead.zip_code,
            'country': lead.country,
            'linkedin_url': lead.linkedin_url,
            'facebook_url': lead.facebook_url,
            'instagram_url': lead.instagram_url,
            'estimated_employees': lead.estimated_employees,
            'founded_year': lead.founded_year,
            'estimated_revenue': lead.estimated_revenue,
            'lead_score': lead.lead_score,
            'lead_quality': lead.lead_quality,
            'confidence_score': lead.confidence_score,
            'email_verification_status': lead.email_verification_status.value if lead.email_verification_status else None,
            'recommended_services': lead.recommended_services,
            'ai_notes': lead.ai_notes,
            'sources_used': lead.sources_used,
            'status': lead.status.value,
        }
        data.append(row)
    
    json_str = json.dumps(data, indent=2, default=str)
    
    filename = f"{batch_name}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    return StreamingResponse(
        io.StringIO(json_str),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/{batch_id}/download")
async def download_export(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get download URL for a previously generated export."""
    # This would typically serve pre-generated files from storage
    # For now, redirect to the export endpoint
    return JSONResponse({
        "message": "Use POST /api/v1/files/export/{batch_id} to generate export",
        "batch_id": batch_id,
    })

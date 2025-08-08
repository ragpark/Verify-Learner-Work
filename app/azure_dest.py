from azure.storage.blob import BlobServiceClient, BlobClient, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta
from .config import settings
import httpx, asyncio

def make_write_sas(blob_name: str, hours: int = 2) -> str:
    sas = generate_blob_sas(
        account_name=settings.AZURE_STORAGE_ACCOUNT,
        container_name=settings.AZURE_BLOB_CONTAINER,
        blob_name=blob_name,
        account_key=settings.AZURE_STORAGE_KEY,
        permission=BlobSasPermissions(write=True, create=True, add=True),
        expiry=datetime.utcnow() + timedelta(hours=hours)
    )
    return f"https://{settings.AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/{settings.AZURE_BLOB_CONTAINER}/{blob_name}?{sas}"

async def stream_copy_to_azure(source_url: str, blob_name: str, auth_header: str = None, chunk_size_mb: int = None):
    sas_url = make_write_sas(blob_name)
    bc = BlobClient.from_blob_url(sas_url)
    chunk_size = (chunk_size_mb or settings.AZURE_BLOB_BLOCK_SIZE_MB) * 1024 * 1024
    headers = {}
    if auth_header:
        headers["Authorization"] = auth_header
    with httpx.stream("GET", source_url, headers=headers, timeout=None) as r:
        r.raise_for_status()
        await asyncio.to_thread(
            bc.upload_blob,
            r.iter_bytes(),
            overwrite=True,
            max_concurrency=settings.AZURE_BLOB_UPLOAD_CONCURRENCY,
            length=None,
            chunk_size=chunk_size
        )
    return sas_url

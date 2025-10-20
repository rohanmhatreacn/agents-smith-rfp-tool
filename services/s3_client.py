"""
S3 client service with support for both MinIO (local development) and AWS S3 (production).
"""
import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from minio import Minio
from minio.error import S3Error
import io

logger = logging.getLogger(__name__)


class S3Client:
    """S3 client that supports both MinIO (local) and AWS S3 (production)."""
    
    def __init__(self):
        self.is_local = os.getenv("S3_LOCAL", "true").lower() == "true"
        self.bucket_name = os.getenv("S3_BUCKET_NAME", "rfp-assistant-documents")
        
        if self.is_local:
            self._setup_minio_client()
        else:
            self._setup_aws_client()
    
    def _setup_minio_client(self):
        """Setup MinIO client for local development."""
        try:
            self.client = Minio(
                'localhost:9000',
                access_key='minioadmin',
                secret_key='minioadmin123',
                secure=False
            )
            logger.info("✅ Connected to MinIO")
        except Exception as e:
            logger.error(f"❌ Failed to connect to MinIO: {e}")
            raise
    
    def _setup_aws_client(self):
        """Setup AWS S3 client for production."""
        try:
            self.client = boto3.client('s3')
            logger.info("✅ Connected to AWS S3")
        except NoCredentialsError:
            logger.error("❌ AWS credentials not found")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to connect to AWS S3: {e}")
            raise
    
    def create_bucket_if_not_exists(self):
        """Create the bucket if it doesn't exist."""
        try:
            if self.is_local:
                # MinIO
                if not self.client.bucket_exists(self.bucket_name):
                    self.client.make_bucket(self.bucket_name)
                    logger.info(f"✅ Created MinIO bucket: {self.bucket_name}")
                else:
                    logger.info(f"✅ MinIO bucket {self.bucket_name} already exists")
            else:
                # AWS S3
                try:
                    self.client.head_bucket(Bucket=self.bucket_name)
                    logger.info(f"✅ AWS S3 bucket {self.bucket_name} already exists")
                except ClientError as e:
                    if e.response['Error']['Code'] == '404':
                        self.client.create_bucket(Bucket=self.bucket_name)
                        logger.info(f"✅ Created AWS S3 bucket: {self.bucket_name}")
                    else:
                        raise
        except Exception as e:
            logger.error(f"❌ Failed to create bucket {self.bucket_name}: {e}")
            raise
    
    def upload_file(self, file_path: str, object_key: str, metadata: Optional[Dict[str, str]] = None) -> bool:
        """Upload a file to S3/MinIO."""
        try:
            if self.is_local:
                # MinIO
                self.client.fput_object(
                    self.bucket_name,
                    object_key,
                    file_path,
                    metadata=metadata or {}
                )
            else:
                # AWS S3
                extra_args = {}
                if metadata:
                    extra_args['Metadata'] = metadata
                
                self.client.upload_file(
                    file_path,
                    self.bucket_name,
                    object_key,
                    ExtraArgs=extra_args
                )
            
            logger.info(f"✅ Uploaded file {file_path} as {object_key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to upload file {file_path}: {e}")
            return False
    
    def upload_file_object(self, file_data: bytes, object_key: str, content_type: str = "application/octet-stream", metadata: Optional[Dict[str, str]] = None) -> bool:
        """Upload file data from memory to S3/MinIO."""
        try:
            file_obj = io.BytesIO(file_data)
            
            if self.is_local:
                # MinIO
                self.client.put_object(
                    self.bucket_name,
                    object_key,
                    file_obj,
                    length=len(file_data),
                    content_type=content_type,
                    metadata=metadata or {}
                )
            else:
                # AWS S3
                extra_args = {'ContentType': content_type}
                if metadata:
                    extra_args['Metadata'] = metadata
                
                self.client.upload_fileobj(
                    file_obj,
                    self.bucket_name,
                    object_key,
                    ExtraArgs=extra_args
                )
            
            logger.info(f"✅ Uploaded file data as {object_key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to upload file data as {object_key}: {e}")
            return False
    
    def download_file(self, object_key: str, file_path: str) -> bool:
        """Download a file from S3/MinIO."""
        try:
            if self.is_local:
                # MinIO
                self.client.fget_object(self.bucket_name, object_key, file_path)
            else:
                # AWS S3
                self.client.download_file(self.bucket_name, object_key, file_path)
            
            logger.info(f"✅ Downloaded {object_key} to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to download {object_key}: {e}")
            return False
    
    def download_file_object(self, object_key: str) -> Optional[bytes]:
        """Download file data from S3/MinIO to memory."""
        try:
            if self.is_local:
                # MinIO
                response = self.client.get_object(self.bucket_name, object_key)
                data = response.read()
                response.close()
                response.release_conn()
            else:
                # AWS S3
                response = self.client.get_object(Bucket=self.bucket_name, Key=object_key)
                data = response['Body'].read()
            
            logger.info(f"✅ Downloaded {object_key} to memory")
            return data
            
        except Exception as e:
            logger.error(f"❌ Failed to download {object_key} to memory: {e}")
            return None
    
    def delete_file(self, object_key: str) -> bool:
        """Delete a file from S3/MinIO."""
        try:
            if self.is_local:
                # MinIO
                self.client.remove_object(self.bucket_name, object_key)
            else:
                # AWS S3
                self.client.delete_object(Bucket=self.bucket_name, Key=object_key)
            
            logger.info(f"✅ Deleted {object_key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete {object_key}: {e}")
            return False
    
    def list_files(self, prefix: str = "", max_keys: int = 1000) -> List[Dict[str, Any]]:
        """List files in the bucket."""
        try:
            files = []
            
            if self.is_local:
                # MinIO
                objects = self.client.list_objects(
                    self.bucket_name,
                    prefix=prefix,
                    recursive=True
                )
                for obj in objects:
                    files.append({
                        'key': obj.object_name,
                        'size': obj.size,
                        'last_modified': obj.last_modified,
                        'etag': obj.etag
                    })
            else:
                # AWS S3
                paginator = self.client.get_paginator('list_objects_v2')
                pages = paginator.paginate(
                    Bucket=self.bucket_name,
                    Prefix=prefix,
                    MaxKeys=max_keys
                )
                
                for page in pages:
                    for obj in page.get('Contents', []):
                        files.append({
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'],
                            'etag': obj['ETag']
                        })
            
            logger.info(f"✅ Listed {len(files)} files")
            return files
            
        except Exception as e:
            logger.error(f"❌ Failed to list files: {e}")
            return []
    
    def file_exists(self, object_key: str) -> bool:
        """Check if a file exists in S3/MinIO."""
        try:
            if self.is_local:
                # MinIO
                self.client.stat_object(self.bucket_name, object_key)
            else:
                # AWS S3
                self.client.head_object(Bucket=self.bucket_name, Key=object_key)
            
            return True
            
        except Exception as e:
            logger.debug(f"File {object_key} does not exist: {e}")
            return False
    
    def get_file_metadata(self, object_key: str) -> Optional[Dict[str, Any]]:
        """Get file metadata from S3/MinIO."""
        try:
            if self.is_local:
                # MinIO
                stat = self.client.stat_object(self.bucket_name, object_key)
                return {
                    'size': stat.size,
                    'last_modified': stat.last_modified,
                    'etag': stat.etag,
                    'content_type': stat.content_type,
                    'metadata': stat.metadata
                }
            else:
                # AWS S3
                response = self.client.head_object(Bucket=self.bucket_name, Key=object_key)
                return {
                    'size': response['ContentLength'],
                    'last_modified': response['LastModified'],
                    'etag': response['ETag'],
                    'content_type': response.get('ContentType'),
                    'metadata': response.get('Metadata', {})
                }
            
        except Exception as e:
            logger.error(f"❌ Failed to get metadata for {object_key}: {e}")
            return None
    
    def generate_presigned_url(self, object_key: str, expiration: int = 3600) -> Optional[str]:
        """Generate a presigned URL for file access."""
        try:
            if self.is_local:
                # MinIO
                url = self.client.presigned_get_object(
                    self.bucket_name,
                    object_key,
                    expires=timedelta(seconds=expiration)
                )
            else:
                # AWS S3
                url = self.client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket_name, 'Key': object_key},
                    ExpiresIn=expiration
                )
            
            logger.info(f"✅ Generated presigned URL for {object_key}")
            return url
            
        except Exception as e:
            logger.error(f"❌ Failed to generate presigned URL for {object_key}: {e}")
            return None
    
    def health_check(self) -> bool:
        """Check if S3/MinIO connection is healthy."""
        try:
            if self.is_local:
                # MinIO
                self.client.list_buckets()
            else:
                # AWS S3
                self.client.list_buckets()
            
            logger.info("✅ S3/MinIO health check passed")
            return True
        except Exception as e:
            logger.error(f"❌ S3/MinIO health check failed: {e}")
            return False


# Global S3 client instance
s3_client = S3Client()
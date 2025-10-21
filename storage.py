import json
import sqlite3
import os
from datetime import datetime
from typing import Any
import logging
from config import config

logger = logging.getLogger(__name__)


class Storage:
    """
    Unified storage interface that auto-routes to local or cloud storage.
    Local: MinIO (S3-compatible) + SQLite
    Cloud: AWS S3 + DynamoDB
    """
    
    def __init__(self):
        """
        Initializes storage clients based on environment.
        Auto-detects local vs cloud and configures appropriate backends.
        """
        self.is_cloud = config.environment == "cloud"
        
        if self.is_cloud:
            self._setup_cloud_storage()
        else:
            self._setup_local_storage()
    
    
    def _setup_cloud_storage(self):
        """
        Sets up AWS S3 and DynamoDB clients for cloud environment.
        Uses IAM roles or environment credentials automatically.
        """
        import boto3
        
        self.s3 = boto3.client('s3', region_name=config.aws_region)
        self.dynamodb = boto3.resource('dynamodb', region_name=config.aws_region)
        self.table = self.dynamodb.Table(config.storage_table)
        
        logger.info(f"✅ Connected to AWS S3 bucket: {config.storage_bucket}")
        logger.info(f"✅ Connected to DynamoDB table: {config.storage_table}")
    
    
    def _setup_local_storage(self):
        """
        Sets up MinIO and SQLite for local development.
        Creates necessary directories and database if they don't exist.
        """
        from minio import Minio
        
        self.s3 = Minio(
            config.minio_endpoint,
            access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            secure=False
        )
        
        os.makedirs(os.path.dirname(config.sqlite_path), exist_ok=True)
        self.db = sqlite3.connect(config.sqlite_path, check_same_thread=False)
        self._init_sqlite_schema()
        
        self._ensure_bucket_exists()
        
        logger.info(f"✅ Connected to MinIO at {config.minio_endpoint}")
        logger.info(f"✅ Using SQLite database at {config.sqlite_path}")
    
    
    def _init_sqlite_schema(self):
        """
        Creates SQLite tables to mimic DynamoDB structure.
        Simple key-value store for session data.
        """
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        self.db.commit()
    
    
    def _ensure_bucket_exists(self):
        """
        Creates the storage bucket in MinIO if it doesn't exist.
        S3-compatible bucket creation for local development.
        """
        try:
            if not self.s3.bucket_exists(config.storage_bucket):
                self.s3.make_bucket(config.storage_bucket)
                logger.info(f"✅ Created bucket: {config.storage_bucket}")
        except Exception as e:
            logger.warning(f"⚠️ Bucket check/creation issue: {e}")
    
    
    def save_file(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
        """
        Saves a file to object storage (S3 or MinIO).
        Returns True if successful, False otherwise.
        """
        try:
            if self.is_cloud:
                self.s3.put_object(
                    Bucket=config.storage_bucket,
                    Key=key,
                    Body=data,
                    ContentType=content_type
                )
            else:
                from io import BytesIO
                self.s3.put_object(
                    config.storage_bucket,
                    key,
                    BytesIO(data),
                    len(data),
                    content_type=content_type
                )
            
            logger.debug(f"✅ Saved file: {key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save file {key}: {e}")
            return False
    
    
    def load_file(self, key: str) -> bytes | None:
        """
        Loads a file from object storage (S3 or MinIO).
        Returns file contents as bytes, or None if not found.
        """
        try:
            if self.is_cloud:
                response = self.s3.get_object(
                    Bucket=config.storage_bucket,
                    Key=key
                )
                return response['Body'].read()
            else:
                response = self.s3.get_object(config.storage_bucket, key)
                return response.read()
                
        except Exception as e:
            logger.error(f"❌ Failed to load file {key}: {e}")
            return None
    
    
    def save_session(self, session_id: str, data: dict) -> bool:
        """
        Saves session data to database (DynamoDB or SQLite).
        Stores metadata, state, and references to large files.
        """
        try:
            data['updated_at'] = datetime.utcnow().isoformat()
            
            if self.is_cloud:
                self.table.put_item(Item={
                    'session_id': session_id,
                    **data
                })
            else:
                self.db.execute(
                    "INSERT OR REPLACE INTO sessions (session_id, data, updated_at) VALUES (?, ?, ?)",
                    (session_id, json.dumps(data, default=str), data['updated_at'])
                )
                self.db.commit()
            
            logger.debug(f"✅ Saved session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save session {session_id}: {e}")
            return False
    
    
    def load_session(self, session_id: str) -> dict | None:
        """
        Loads session data from database (DynamoDB or SQLite).
        Returns session data dict, or None if not found.
        """
        try:
            if self.is_cloud:
                response = self.table.get_item(Key={'session_id': session_id})
                return response.get('Item')
            else:
                cursor = self.db.execute(
                    "SELECT data FROM sessions WHERE session_id = ?",
                    (session_id,)
                )
                row = cursor.fetchone()
                return json.loads(row[0]) if row else None
                
        except Exception as e:
            logger.error(f"❌ Failed to load session {session_id}: {e}")
            return None


storage = Storage()


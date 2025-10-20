"""
DynamoDB client service with support for both local development and AWS production.
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger(__name__)


class DynamoDBClient:
    """DynamoDB client that supports both local development and AWS production."""
    
    def __init__(self):
        self.is_local = os.getenv("DYNAMODB_LOCAL", "true").lower() == "true"
        self.table_name = os.getenv("DYNAMODB_TABLE_NAME", "rfp-assistant-sessions")
        
        if self.is_local:
            self._setup_local_client()
        else:
            self._setup_aws_client()
    
    def _setup_local_client(self):
        """Setup DynamoDB client for local development."""
        try:
            self.dynamodb = boto3.resource(
                'dynamodb',
                endpoint_url='http://localhost:8000',
                region_name='us-east-1',
                aws_access_key_id='dummy',
                aws_secret_access_key='dummy'
            )
            logger.info("✅ Connected to local DynamoDB")
        except Exception as e:
            logger.error(f"❌ Failed to connect to local DynamoDB: {e}")
            raise
    
    def _setup_aws_client(self):
        """Setup DynamoDB client for AWS production."""
        try:
            self.dynamodb = boto3.resource('dynamodb')
            logger.info("✅ Connected to AWS DynamoDB")
        except NoCredentialsError:
            logger.error("❌ AWS credentials not found")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to connect to AWS DynamoDB: {e}")
            raise
    
    def create_table_if_not_exists(self):
        """Create the sessions table if it doesn't exist."""
        try:
            # Check if table exists
            self.dynamodb.Table(self.table_name).load()
            logger.info(f"✅ Table {self.table_name} already exists")
            return
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Table doesn't exist, create it
                self._create_table()
            else:
                logger.error(f"❌ Error checking table existence: {e}")
                raise
    
    def _create_table(self):
        """Create the sessions table."""
        try:
            table = self.dynamodb.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {
                        'AttributeName': 'session_id',
                        'KeyType': 'HASH'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'session_id',
                        'AttributeType': 'S'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            # Wait for table to be created
            table.wait_until_exists()
            logger.info(f"✅ Created table {self.table_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create table {self.table_name}: {e}")
            raise
    
    def save_session_data(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Save session data to DynamoDB."""
        try:
            table = self.dynamodb.Table(self.table_name)
            
            item = {
                'session_id': session_id,
                'data': json.dumps(data),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            table.put_item(Item=item)
            logger.info(f"✅ Saved session data for {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save session data for {session_id}: {e}")
            return False
    
    def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data from DynamoDB."""
        try:
            table = self.dynamodb.Table(self.table_name)
            
            response = table.get_item(
                Key={'session_id': session_id}
            )
            
            if 'Item' in response:
                data = json.loads(response['Item']['data'])
                logger.info(f"✅ Retrieved session data for {session_id}")
                return data
            else:
                logger.info(f"ℹ️ No session data found for {session_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to retrieve session data for {session_id}: {e}")
            return None
    
    def update_session_data(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Update session data in DynamoDB."""
        try:
            table = self.dynamodb.Table(self.table_name)
            
            # First check if session exists
            existing_data = self.get_session_data(session_id)
            if existing_data is None:
                logger.warning(f"⚠️ Session {session_id} not found, creating new session")
                return self.save_session_data(session_id, data)
            
            # Update existing session
            table.update_item(
                Key={'session_id': session_id},
                UpdateExpression='SET #data = :data, updated_at = :updated_at',
                ExpressionAttributeNames={'#data': 'data'},
                ExpressionAttributeValues={
                    ':data': json.dumps(data),
                    ':updated_at': datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"✅ Updated session data for {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update session data for {session_id}: {e}")
            return False
    
    def delete_session_data(self, session_id: str) -> bool:
        """Delete session data from DynamoDB."""
        try:
            table = self.dynamodb.Table(self.table_name)
            
            table.delete_item(
                Key={'session_id': session_id}
            )
            
            logger.info(f"✅ Deleted session data for {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete session data for {session_id}: {e}")
            return False
    
    def list_sessions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all sessions with pagination."""
        try:
            table = self.dynamodb.Table(self.table_name)
            
            response = table.scan(
                Limit=limit,
                ProjectionExpression='session_id, created_at, updated_at'
            )
            
            sessions = []
            for item in response.get('Items', []):
                sessions.append({
                    'session_id': item['session_id'],
                    'created_at': item.get('created_at'),
                    'updated_at': item.get('updated_at')
                })
            
            logger.info(f"✅ Listed {len(sessions)} sessions")
            return sessions
            
        except Exception as e:
            logger.error(f"❌ Failed to list sessions: {e}")
            return []
    
    def health_check(self) -> bool:
        """Check if DynamoDB connection is healthy."""
        try:
            # Try to list tables to check if DynamoDB is accessible
            self.dynamodb.meta.client.list_tables()
            logger.info("✅ DynamoDB health check passed")
            return True
        except Exception as e:
            logger.error(f"❌ DynamoDB health check failed: {e}")
            return False


# Global DynamoDB client instance
dynamodb_client = DynamoDBClient()
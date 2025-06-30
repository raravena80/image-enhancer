import boto3
import os
import tempfile
import base64
from PIL import Image
from openai import OpenAI
from botocore.exceptions import ClientError
import logging
from temporalio import activity
from dataclasses import dataclass
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ImageProcessingConfig:
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = 'us-east-1'
    openai_api_key: Optional[str] = None

@dataclass
class S3Location:
    bucket: str
    key: str

@activity.defn
async def download_image_from_s3(config: ImageProcessingConfig, s3_location: S3Location) -> str:
    """
    Download an image from S3 bucket to a temporary file.
    
    Args:
        config: Configuration for AWS and OpenAI
        s3_location: S3 bucket and key information
        
    Returns:
        str: Path to the downloaded temporary file
    """
    try:
        logger.info(f"Downloading image from s3://{s3_location.bucket}/{s3_location.key}")
        
        # Initialize AWS S3 client
        # Use credentials from config if provided, otherwise fall back to environment/IAM
        if config.aws_access_key_id and config.aws_secret_access_key:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=config.aws_access_key_id,
                aws_secret_access_key=config.aws_secret_access_key,
                region_name=config.aws_region
            )
        else:
            # Use environment variables or IAM role
            s3_client = boto3.client(
                's3', 
                region_name=config.aws_region,
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )

        logger.info(f"config HERE: {config}")
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        temp_file_path = temp_file.name
        temp_file.close()
        
        # Download the file from S3
        s3_client.download_file(s3_location.bucket, s3_location.key, temp_file_path)
        
        logger.info(f"Image downloaded to temporary file: {temp_file_path}")
        return temp_file_path
        
    except ClientError as e:
        logger.error(f"Error downloading from S3: {e}")
        raise

@activity.defn
async def enhance_image_with_openai(config: ImageProcessingConfig, image_path: str, 
                                  enhancement_prompt: str = "Enhance this image to make it more vibrant and clear") -> str:
    """
    Enhance image using OpenAI's DALL-E API.
    
    Args:
        config: Configuration for AWS and OpenAI
        image_path: Path to the input image file
        enhancement_prompt: Prompt for image enhancement
        
    Returns:
        str: Path to the enhanced image file
    """
    try:
        logger.info("Enhancing image with OpenAI...")
        
        # Initialize OpenAI client
        openai_client = OpenAI(
            api_key=config.openai_api_key or os.getenv('OPENAI_API_KEY')
        )
        
        # Create a temporary file for the enhanced image
        enhanced_temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        enhanced_file_path = enhanced_temp_file.name
        enhanced_temp_file.close()
        
        # Use OpenAI's image editing endpoint
        response = openai_client.images.edit(
            image=open(image_path, 'rb'),
            prompt=enhancement_prompt,
            n=1,
            size="1024x1024",
            model="gpt-image-1"            
        )
        
        # Check if response is valid and get the enhanced image base64
        if not response or not response.data:
            raise Exception("OpenAI API returned no data")
        enhanced_image_base64 = response.data[0].b64_json
        if not enhanced_image_base64:
            raise Exception("No base64 image data returned from OpenAI")

        # Download the enhanced image to the temporary file
        enhanced_image_data = base64.b64decode(enhanced_image_base64)
        with open(enhanced_file_path, 'wb') as f:
            f.write(enhanced_image_data)
        
        logger.info(f"Image enhancement completed: {enhanced_file_path}")
        return enhanced_file_path
        
    except Exception as e:
        logger.error(f"Error enhancing image with OpenAI: {e}")
        raise

@activity.defn
async def upload_image_to_s3(config: ImageProcessingConfig, image_path: str, 
                           s3_location: S3Location, content_type: str = 'image/jpeg') -> None:
    """
    Upload image file to S3 bucket.
    
    Args:
        config: Configuration for AWS and OpenAI
        image_path: Path to the image file
        s3_location: S3 bucket and key information
        content_type: MIME type of the image
    """
    try:
        logger.info(f"Uploading processed image to s3://{s3_location.bucket}/{s3_location.key}")
        
        # Initialize AWS S3 client
        # Use credentials from config if provided, otherwise fall back to environment/IAM
        if config.aws_access_key_id and config.aws_secret_access_key:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=config.aws_access_key_id,
                aws_secret_access_key=config.aws_secret_access_key,
                region_name=config.aws_region
            )
        else:
            # Use environment variables or IAM role
            s3_client = boto3.client(
                's3', 
                region_name=config.aws_region,
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
        
        # Determine content type based on file extension if not provided
        if content_type == 'image/jpeg':
            if image_path.lower().endswith('.png'):
                content_type = 'image/png'
            elif image_path.lower().endswith('.webp'):
                content_type = 'image/webp'
        
        # Upload the file to S3
        s3_client.upload_file(
            image_path, 
            s3_location.bucket, 
            s3_location.key,
            ExtraArgs={'ContentType': content_type}
        )
        
        logger.info("Upload completed successfully")
        
    except ClientError as e:
        logger.error(f"Error uploading to S3: {e}")
        raise

@activity.defn
async def cleanup_temp_file(file_path: str) -> None:
    """
    Clean up a temporary file.
    
    Args:
        file_path: Path to the file to delete
    """
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            logger.info(f"Cleaned up temporary file: {file_path}")
    except Exception as e:
        logger.warning(f"Could not delete temporary file {file_path}: {e}")

"""
This module provides the ImageEnhancer class for processing and enhancing images using AWS S3 and OpenAI's DALL-E API.

Features:
- Download images from S3
- Enhance images using OpenAI
- Upload enhanced images back to S3
- Utility methods for image conversion and cleanup

Intended for use as a standalone script or as an importable module for image enhancement workflows.
"""
import boto3
import os
import requests
import tempfile
from PIL import Image
import base64
from openai import OpenAI
from dotenv import load_dotenv
from botocore.exceptions import ClientError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ImageEnhancer:
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 aws_region='us-east-1', openai_api_key=None):
        """
        Initialize the ImageEnhancer with AWS and OpenAI credentials.

        Args:
            aws_access_key_id: AWS access key (if None, uses environment or IAM role)
            aws_secret_access_key: AWS secret key (if None, uses environment or IAM role)
            aws_region: AWS region
            openai_api_key: OpenAI API key (if None, uses environment variable)
        """
        # Initialize AWS S3 client
        if aws_access_key_id and aws_secret_access_key:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=aws_region
            )
        else:
            self.s3_client = boto3.client('s3', region_name=aws_region)

        # Initialize OpenAI client
        self.openai_client = OpenAI(
            api_key=openai_api_key or os.getenv('OPENAI_API_KEY')
        )

    def download_image_from_s3(self, bucket_name, object_key):
        """
        Download an image from S3 bucket to a temporary file.

        Args:
            bucket_name: Name of the S3 bucket
            object_key: Key/path of the object in S3

        Returns:
            str: Path to the downloaded temporary file
        """
        try:
            logger.info(f"Downloading image from s3://{bucket_name}/{object_key}")

            # Create a temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            temp_file_path = temp_file.name
            temp_file.close()

            # Download the file from S3
            self.s3_client.download_file(bucket_name, object_key, temp_file_path)

            logger.info(f"Image downloaded to temporary file: {temp_file_path}")
            return temp_file_path

        except ClientError as e:
            logger.error(f"Error downloading from S3 (bucket={bucket_name}, key={object_key}): {e}")
            raise

    def image_to_base64(self, image_path):
        """
        Convert image file to base64 string.

        Args:
            image_path: Path to the image file

        Returns:
            str: Base64 encoded image
        """
        with open(image_path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def enhance_image_with_openai(self, image_path, enhancement_prompt="Enhance this image to make it more vibrant and clear"):
        """
        Enhance image using OpenAI's DALL-E API.

        Args:
            image_path: Path to the input image file
            enhancement_prompt: Prompt for image enhancement

        Returns:
            str: Path to the enhanced image file
        """
        try:
            logger.info("Enhancing image with OpenAI...")

            # Create a temporary file for the enhanced image
            enhanced_temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            enhanced_file_path = enhanced_temp_file.name
            enhanced_temp_file.close()

            response = self.openai_client.images.edit(
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
            logger.error(f"Error enhancing image with OpenAI (image_path={image_path}, prompt={enhancement_prompt}): {e}")
            raise

    def upload_image_to_s3(self, image_path, bucket_name, object_key, content_type='image/jpeg'):
        """
        Upload image file to S3 bucket.

        Args:
            image_path: Path to the image file
            bucket_name: Name of the destination S3 bucket
            object_key: Key/path for the object in S3
            content_type: MIME type of the image
        """
        try:
            logger.info(f"Uploading processed image to s3://{bucket_name}/{object_key}")

            # Determine content type based on file extension if not provided
            if content_type == 'image/jpeg':
                if image_path.lower().endswith('.png'):
                    content_type = 'image/png'
                elif image_path.lower().endswith('.webp'):
                    content_type = 'image/webp'

            # Upload the file to S3
            self.s3_client.upload_file(
                image_path,
                bucket_name,
                object_key,
                ExtraArgs={'ContentType': content_type}
            )

            logger.info("Upload completed successfully")

        except ClientError as e:
            logger.error(f"Error uploading to S3 (bucket={bucket_name}, key={object_key}, image_path={image_path}): {e}")
            raise

    def cleanup_temp_files(self, *file_paths):
        """
        Clean up temporary files.

        Args:
            *file_paths: Variable number of file paths to delete
        """
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    logger.info(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Could not delete temporary file {file_path}: {e}")

    def process_image(self, source_bucket, source_key, dest_bucket, dest_key,
                     enhancement_prompt="Enhance this image to make it more vibrant and clear"):
        """
        Complete workflow: download, enhance, and upload image.

        Args:
            source_bucket: Source S3 bucket name
            source_key: Source object key
            dest_bucket: Destination S3 bucket name
            dest_key: Destination object key
            enhancement_prompt: Prompt for image enhancement
        """
        original_image_path = None
        enhanced_image_path = None

        try:
            # Step 1: Download image from S3
            original_image_path = self.download_image_from_s3(source_bucket, source_key)

            # Step 2: Enhance image with OpenAI
            enhanced_image_path = self.enhance_image_with_openai(original_image_path, enhancement_prompt)

            # Step 3: Upload enhanced image to S3
            self.upload_image_to_s3(enhanced_image_path, dest_bucket, dest_key)

            logger.info(f"Successfully processed image: {source_bucket}/{source_key} -> {dest_bucket}/{dest_key}")

        except Exception as e:
            logger.error(f"Error in image processing workflow (source={source_bucket}/{source_key}, dest={dest_bucket}/{dest_key}, step=process_image): {e}")
            raise
        finally:
            # Clean up temporary files
            if original_image_path or enhanced_image_path:
                self.cleanup_temp_files(original_image_path, enhanced_image_path)

def main():
    """
    Example usage of the ImageEnhancer class.
    """
    # Configuration
    SOURCE_BUCKET = os.getenv("SOURCE_BUCKET")
    SOURCE_KEY = os.getenv("SOURCE_KEY")
    DEST_BUCKET = os.getenv("DEST_BUCKET")
    DEST_KEY = os.getenv("DEST_KEY")

    # Enhancement prompt
    ENHANCEMENT_PROMPT = os.getenv("ENHANCEMENT_PROMPT")
    if not ENHANCEMENT_PROMPT:
        ENHANCEMENT_PROMPT = "Make this image more vibrant, increase clarity and sharpness, improve lighting"

    keyid = os.getenv("AWS_ACCESS_KEY_ID")
    secretid = os.getenv("AWS_SECRET_ACCESS_KEY")

    try:
        # Initialize the enhancer
        enhancer = ImageEnhancer(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_region='us-east-1',  # Change to your preferred region
            # openai_api_key='your-openai-api-key'  # Or set OPENAI_API_KEY environment variable
        )

        # Process the image
        enhancer.process_image(
            source_bucket=SOURCE_BUCKET,
            source_key=SOURCE_KEY,
            dest_bucket=DEST_BUCKET,
            dest_key=DEST_KEY,
            enhancement_prompt=ENHANCEMENT_PROMPT
        )

        logger.info("Image processing completed successfully!")

    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    main()

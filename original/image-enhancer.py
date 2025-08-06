#!/usr/bin/env python3

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
import time
from tqdm import tqdm
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ImageEnhancer:
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 aws_region='us-east-1', openai_api_key=None, show_progress=True):
        """
        Initialize the ImageEnhancer with AWS and OpenAI credentials.

        Args:
            aws_access_key_id: AWS access key (if None, uses environment or IAM role)
            aws_secret_access_key: AWS secret key (if None, uses environment or IAM role)
            aws_region: AWS region
            openai_api_key: OpenAI API key (if None, uses environment variable)
            show_progress: Whether to display progress bars during operations
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

        # Progress configuration
        self.show_progress = show_progress

        # Estimated durations for each step (in seconds) - these can be tuned based on experience
        self.step_durations = {
            'download': 5,      # S3 download usually takes a few seconds
            'enhance': 30,      # OpenAI enhancement takes the longest, average ~30 seconds
            'upload': 3         # S3 upload is usually quick
        }

        # Store original logging level for restoration
        self._original_log_level = logger.level

    def _create_progress_bar(self, description, duration_seconds):
        """
        Create a progress bar for a given operation.

        Args:
            description: Description of the operation
            duration_seconds: Estimated duration in seconds

        Returns:
            tqdm progress bar object or None if progress is disabled
        """
        if not self.show_progress:
            return None

        return tqdm(
            total=100,
            desc=description,
            unit="%",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
            ncols=100,
            leave=False,
            dynamic_ncols=True
        )

    def _simulate_progress(self, progress_bar, duration_seconds, step_count=20):
        """
        Simulate progress updates for operations where we can't track actual progress.

        Args:
            progress_bar: tqdm progress bar object
            duration_seconds: Total estimated duration
            step_count: Number of progress updates to make
        """
        if not progress_bar:
            return

        step_duration = duration_seconds / step_count
        step_size = 100 / step_count

        for i in range(step_count):
            time.sleep(step_duration)
            progress_bar.update(step_size)

        progress_bar.close()

    def _quiet_logging(self):
        """Temporarily reduce logging level during progress display."""
        if self.show_progress:
            logger.setLevel(logging.WARNING)
            # Also quiet boto3 and other noisy loggers
            logging.getLogger('boto3').setLevel(logging.WARNING)
            logging.getLogger('botocore').setLevel(logging.WARNING)
            logging.getLogger('urllib3').setLevel(logging.WARNING)
            logging.getLogger('httpx').setLevel(logging.WARNING)

    def _restore_logging(self):
        """Restore original logging level."""
        if self.show_progress:
            logger.setLevel(self._original_log_level)
            logging.getLogger('boto3').setLevel(logging.INFO)
            logging.getLogger('botocore').setLevel(logging.INFO)
            logging.getLogger('urllib3').setLevel(logging.INFO)
            logging.getLogger('httpx').setLevel(logging.INFO)

    def download_image_from_s3(self, bucket_name, object_key):
        """
        Download an image from S3 bucket to a temporary file.

        Args:
            bucket_name: Name of the S3 bucket
            object_key: Key/path of the object in S3

        Returns:
            str: Path to the downloaded temporary file
        """
        progress_bar = self._create_progress_bar("Downloading image from S3", self.step_durations['download'])

        try:
            logger.info(f"Downloading image from s3://{bucket_name}/{object_key}")

            if self.show_progress:
                self._quiet_logging()

            # Create a temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            temp_file_path = temp_file.name
            temp_file.close()

            if progress_bar:
                progress_bar.update(20)  # Show progress for temp file creation

            # Download the file from S3
            start_time = time.time()
            self.s3_client.download_file(bucket_name, object_key, temp_file_path)
            actual_duration = time.time() - start_time

            if progress_bar:
                progress_bar.update(80)  # Complete the progress bar
                progress_bar.close()

            if self.show_progress:
                self._restore_logging()

            logger.info(f"Image downloaded to temporary file: {temp_file_path} (took {actual_duration:.2f}s)")
            return temp_file_path

        except ClientError as e:
            if self.show_progress:
                self._restore_logging()
            if progress_bar:
                progress_bar.close()
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
        progress_bar = self._create_progress_bar("Enhancing image with OpenAI", self.step_durations['enhance'])

        try:
            logger.info("Enhancing image with OpenAI...")

            if self.show_progress:
                self._quiet_logging()

            # Create a temporary file for the enhanced image
            enhanced_temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            enhanced_file_path = enhanced_temp_file.name
            enhanced_temp_file.close()

            if progress_bar:
                progress_bar.update(10)  # Show progress for setup

            start_time = time.time()

            # Start a thread to simulate progress during the OpenAI API call
            import threading
            if progress_bar:
                def simulate_api_progress():
                    # Simulate gradual progress during API call
                    for i in range(9):  # 9 steps to reach 90% total
                        time.sleep(self.step_durations['enhance'] / 12)  # Spread over most of the duration
                        if progress_bar.n < 90:  # Don't exceed 90% until we're actually done
                            progress_bar.update(10)

                progress_thread = threading.Thread(target=simulate_api_progress)
                progress_thread.daemon = True
                progress_thread.start()

            response = self.openai_client.images.edit(
                image=open(image_path, 'rb'),
                prompt=enhancement_prompt,
                n=1,
                size="1024x1024",
                model="gpt-image-1"
            )

            actual_duration = time.time() - start_time

            # Check if response is valid and get the enhanced image base64
            if not response or not response.data:
                raise Exception("OpenAI API returned no data")
            enhanced_image_base64 = response.data[0].b64_json
            if not enhanced_image_base64:
                raise Exception("No base64 image data returned from OpenAI")

            if progress_bar:
                # Ensure we're at least at 90% before final steps
                progress_bar.n = max(progress_bar.n, 90)
                progress_bar.refresh()

            # Download the enhanced image to the temporary file
            enhanced_image_data = base64.b64decode(enhanced_image_base64)
            with open(enhanced_file_path, 'wb') as f:
                f.write(enhanced_image_data)

            if progress_bar:
                progress_bar.update(100 - progress_bar.n)  # Complete the progress bar
                progress_bar.close()

            if self.show_progress:
                self._restore_logging()

            logger.info(f"Image enhancement completed: {enhanced_file_path} (took {actual_duration:.2f}s)")
            return enhanced_file_path

        except Exception as e:
            if self.show_progress:
                self._restore_logging()
            if progress_bar:
                progress_bar.close()
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
        progress_bar = self._create_progress_bar("Uploading enhanced image to S3", self.step_durations['upload'])

        try:
            logger.info(f"Uploading processed image to s3://{bucket_name}/{object_key}")

            if self.show_progress:
                self._quiet_logging()

            # Determine content type based on file extension if not provided
            if content_type == 'image/jpeg':
                if image_path.lower().endswith('.png'):
                    content_type = 'image/png'
                elif image_path.lower().endswith('.webp'):
                    content_type = 'image/webp'

            if progress_bar:
                progress_bar.update(20)  # Show progress for content type detection

            # Upload the file to S3
            start_time = time.time()
            self.s3_client.upload_file(
                image_path,
                bucket_name,
                object_key,
                ExtraArgs={'ContentType': content_type}
            )
            actual_duration = time.time() - start_time

            if progress_bar:
                progress_bar.update(80)  # Complete the progress bar
                progress_bar.close()

            if self.show_progress:
                self._restore_logging()

            logger.info(f"Upload completed successfully (took {actual_duration:.2f}s)")

        except ClientError as e:
            if self.show_progress:
                self._restore_logging()
            if progress_bar:
                progress_bar.close()
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

        # Create overall workflow progress bar
        total_duration = sum(self.step_durations.values())
        overall_progress = None
        if self.show_progress:
            print(f"\n🚀 Starting image enhancement workflow for: {source_key}")
            print(f"   Estimated total time: ~{total_duration} seconds\n")
            overall_progress = tqdm(
                total=3,
                desc="Overall Progress",
                unit="step",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} steps [{elapsed}<{remaining}]",
                ncols=100,
                position=0,
                leave=True,
                dynamic_ncols=True
            )

        try:
            start_time = time.time()

            # Step 1: Download image from S3
            if overall_progress:
                overall_progress.set_description("Overall Progress - Downloading")
            original_image_path = self.download_image_from_s3(source_bucket, source_key)
            if overall_progress:
                overall_progress.update(1)

            # Step 2: Enhance image with OpenAI
            if overall_progress:
                overall_progress.set_description("Overall Progress - Enhancing")
            enhanced_image_path = self.enhance_image_with_openai(original_image_path, enhancement_prompt)
            if overall_progress:
                overall_progress.update(1)

            # Step 3: Upload enhanced image to S3
            if overall_progress:
                overall_progress.set_description("Overall Progress - Uploading")
            self.upload_image_to_s3(enhanced_image_path, dest_bucket, dest_key)
            if overall_progress:
                overall_progress.update(1)
                overall_progress.set_description("Overall Progress - Complete!")

            total_time = time.time() - start_time

            if overall_progress:
                overall_progress.close()
                print(f"\n✅ Successfully processed image in {total_time:.2f} seconds!")
                print(f"   Source: s3://{source_bucket}/{source_key}")
                print(f"   Destination: s3://{dest_bucket}/{dest_key}")

            logger.info(f"Successfully processed image: {source_bucket}/{source_key} -> {dest_bucket}/{dest_key} (total time: {total_time:.2f}s)")

        except Exception as e:
            if overall_progress:
                overall_progress.close()
                print(f"\nError during image processing: {e}")
            logger.error(f"Error in image processing workflow (source={source_bucket}/{source_key}, dest={dest_bucket}/{dest_key}, step=process_image): {e}")
            raise
        finally:
            # Clean up temporary files
            if original_image_path or enhanced_image_path:
                self.cleanup_temp_files(original_image_path, enhanced_image_path)

def main():
    """
    Example usage of the ImageEnhancer class with command line argument support.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Enhanced S3 Image Processing with OpenAI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use with progress bars (default)
  python image-enhancer.py --source-bucket my-bucket --source-key image.jpg --dest-bucket output-bucket --dest-key enhanced.jpg

  # Use without progress bars (original logging)
  python image-enhancer.py --source-bucket my-bucket --source-key image.jpg --dest-bucket output-bucket --dest-key enhanced.jpg --no-progress

  # Use environment variables (can be mixed with command line args)
  SOURCE_BUCKET=my-bucket SOURCE_KEY=image.jpg python image-enhancer.py --dest-bucket output-bucket --dest-key enhanced.jpg

Environment Variables:
  SOURCE_BUCKET        - Source S3 bucket name
  SOURCE_KEY          - Source object key/path
  DEST_BUCKET         - Destination S3 bucket name
  DEST_KEY            - Destination object key/path
  ENHANCEMENT_PROMPT  - Custom enhancement prompt
  AWS_ACCESS_KEY_ID   - AWS credentials
  AWS_SECRET_ACCESS_KEY - AWS credentials
  AWS_DEFAULT_REGION  - AWS region (default: us-east-1)
  OPENAI_API_KEY      - OpenAI API key
        """
    )

    parser.add_argument('--source-bucket',
                       help='Source S3 bucket name')
    parser.add_argument('--source-key',
                       help='Source object key/path')
    parser.add_argument('--dest-bucket',
                       help='Destination S3 bucket name')
    parser.add_argument('--dest-key',
                       help='Destination object key/path')
    parser.add_argument('--enhancement-prompt',
                       help='Custom enhancement prompt')
    parser.add_argument('--aws-region',
                       default='us-east-1',
                       help='AWS region (default: us-east-1)')

    # Progress bar option
    progress_group = parser.add_mutually_exclusive_group()
    progress_group.add_argument('--progress',
                               action='store_true',
                               default=True,
                               help='Show progress bars (default)')
    progress_group.add_argument('--no-progress',
                               action='store_false',
                               dest='progress',
                               help='Disable progress bars, show detailed logging')

    args = parser.parse_args()

    # Get configuration from command line args or environment variables
    SOURCE_BUCKET = args.source_bucket or os.getenv("SOURCE_BUCKET")
    SOURCE_KEY = args.source_key or os.getenv("SOURCE_KEY")
    DEST_BUCKET = args.dest_bucket or os.getenv("DEST_BUCKET")
    DEST_KEY = args.dest_key or os.getenv("DEST_KEY")

    # Enhancement prompt
    ENHANCEMENT_PROMPT = args.enhancement_prompt or os.getenv("ENHANCEMENT_PROMPT")
    if not ENHANCEMENT_PROMPT:
        ENHANCEMENT_PROMPT = "Make this image more vibrant, increase clarity and sharpness, improve lighting"

    # Validate required parameters
    required_params = {
        'SOURCE_BUCKET': SOURCE_BUCKET,
        'SOURCE_KEY': SOURCE_KEY,
        'DEST_BUCKET': DEST_BUCKET,
        'DEST_KEY': DEST_KEY
    }

    missing_params = [name for name, value in required_params.items() if not value]
    if missing_params:
        print(f"Error: Missing required parameters: {', '.join(missing_params)}")
        print("Use --help for usage information")
        return 1

    try:
        # Initialize the enhancer with progress bar setting
        enhancer = ImageEnhancer(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_region=args.aws_region,
            show_progress=args.progress  # Use command line argument
        )

        # Process the image
        enhancer.process_image(
            source_bucket=SOURCE_BUCKET,
            source_key=SOURCE_KEY,
            dest_bucket=DEST_BUCKET,
            dest_key=DEST_KEY,
            enhancement_prompt=ENHANCEMENT_PROMPT
        )

        if not args.progress:
            logger.info("Image processing completed successfully!")

        return 0

    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())

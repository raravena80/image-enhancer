"""
This module defines the Temporal workflow for image enhancement.

The workflow orchestrates the following steps:
- Download image from S3
- Enhance image using OpenAI
- Upload enhanced image to S3
- Cleanup temporary files

Intended for use with Temporal workers and activities for automated image processing pipelines.
"""
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from activities import (
    download_image_from_s3,
    enhance_image_with_openai,
    upload_image_to_s3,
    cleanup_temp_file,
    ImageProcessingConfig,
    S3Location
)
import logging

logger = logging.getLogger(__name__)

@workflow.defn(name="ImageEnhancementWorkflow", sandboxed=False)
class ImageEnhancementWorkflow:
    """
    Temporal workflow for processing images: download from S3, enhance with OpenAI, upload to S3.
    """
    
    @workflow.run
    async def run(self, 
                  config: ImageProcessingConfig,
                  source_location: S3Location,
                  dest_location: S3Location,
                  enhancement_prompt: str = "Enhance this image to make it more vibrant and clear") -> str:
        """
        Main workflow execution method.
        
        Args:
            config: Configuration for AWS and OpenAI
            source_location: Source S3 location
            dest_location: Destination S3 location
            enhancement_prompt: Prompt for image enhancement
            
        Returns:
            str: Success message with processed image location
        """
        
        # Define retry policy for activities
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(minutes=5),
            maximum_attempts=3
        )
        
        original_image_path = None
        enhanced_image_path = None
        
        try:
            workflow.logger.info(f"Starting image enhancement workflow for {source_location.bucket}/{source_location.key}")
            
            # Step 1: Download image from S3
            workflow.logger.info("Step 1: Downloading image from S3")
            original_image_path = await workflow.execute_activity(
                download_image_from_s3,
                args=[config, source_location],
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=retry_policy
            )
            
            # Step 2: Enhance image with OpenAI
            workflow.logger.info("Step 2: Enhancing image with OpenAI")
            enhanced_image_path = await workflow.execute_activity(
                enhance_image_with_openai,
                args=[config, original_image_path, enhancement_prompt],
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=retry_policy
            )
            
            # Step 3: Upload enhanced image to S3
            workflow.logger.info("Step 3: Uploading enhanced image to S3")
            await workflow.execute_activity(
                upload_image_to_s3,
                args=[config, enhanced_image_path, dest_location, "image/png"],
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=retry_policy
            )
            
            workflow.logger.info(f"Successfully processed image: {source_location.bucket}/{source_location.key} -> {dest_location.bucket}/{dest_location.key}")
            
            return f"Successfully processed image: s3://{source_location.bucket}/{source_location.key} -> s3://{dest_location.bucket}/{dest_location.key}"
            
        except Exception as e:
            workflow.logger.error(f"Error in image processing workflow: {e}")
            raise
        finally:
            # Clean up temporary files (fire and forget)
            if original_image_path:
                try:
                    await workflow.execute_activity(
                        cleanup_temp_file,
                        args=[original_image_path],
                        start_to_close_timeout=timedelta(minutes=1),
                        retry_policy=RetryPolicy(maximum_attempts=1)  # Don't retry cleanup
                    )
                except Exception as e:
                    workflow.logger.warning(f"Failed to cleanup original temp file: {e}")
            
            if enhanced_image_path:
                try:
                    await workflow.execute_activity(
                        cleanup_temp_file,
                        args=[enhanced_image_path],
                        start_to_close_timeout=timedelta(minutes=1),
                        retry_policy=RetryPolicy(maximum_attempts=1)  # Don't retry cleanup
                    )
                except Exception as e:
                    workflow.logger.warning(f"Failed to cleanup enhanced temp file: {e}")

#!/usr/bin/env python3

"""
This script runs batch image enhancement workflows using Temporal.

It parses image configuration, connects to the Temporal server, and
manages the execution of multiple image enhancement workflows in parallel or sequentially.
"""
import asyncio
import logging
from temporalio.client import Client, RetryConfig, KeepAliveConfig
from workflows import ImageEnhancementWorkflow
from activities import ImageProcessingConfig, S3Location
import os
from dotenv import load_dotenv
import uuid
import json
from typing import List, Dict, Any
from concurrent.futures import as_completed
import time
import argparse
from tqdm import tqdm
from datetime import timedelta


# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

def setup_logging(show_progress=False):
    """Setup logging configuration based on progress bar setting."""
    if show_progress:
        # Quiet mode for progress bars - reduce logging to warnings only
        logging.basicConfig(level=logging.WARNING, format='%(message)s', force=True)
        # Also quiet temporal and other noisy loggers
        logging.getLogger('temporalio').setLevel(logging.WARNING)
        logging.getLogger('grpc').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        # Set the main module logger level as well
        logging.getLogger(__name__).setLevel(logging.WARNING)
    else:
        # Normal logging mode
        log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            force=True
        )

        # Enable debug logging for Temporal if requested
        if os.getenv('TEMPORAL_DEBUG', '').lower() == 'true':
            logging.getLogger('temporalio').setLevel(logging.DEBUG)
            logger.info("🔍 Temporal debug logging enabled")

def parse_image_list(images_config: str) -> List[Dict[str, str]]:
    """
    Parse image configuration from environment variable.
    Supports both JSON format and simple comma-separated format.

    JSON format:
    [{"source_bucket": "bucket1", "source_key": "image1.jpg", "dest_bucket": "bucket2", "dest_key": "enhanced_image1.jpg"}, ...]

    Simple format (uses default buckets):
    image1.jpg,image2.png,folder/image3.jpeg
    """
    if not images_config:
        return []

    # Try to parse as JSON first
    try:
        images = json.loads(images_config)
        if isinstance(images, list):
            return images
    except json.JSONDecodeError:
        pass

    # Parse as comma-separated list
    source_bucket = os.getenv('SOURCE_BUCKET', 'source-bucket')
    dest_bucket = os.getenv('DEST_BUCKET', 'dest-bucket')

    image_keys = [key.strip() for key in images_config.split(',') if key.strip()]
    images = []

    for key in image_keys:
        # Generate destination key by adding 'enhanced_' prefix
        dest_key = f"enhanced_{os.path.basename(key)}"
        if '/' in key:
            # Preserve folder structure
            folder = os.path.dirname(key)
            dest_key = f"{folder}/enhanced_{os.path.basename(key)}"

        images.append({
            "source_bucket": source_bucket,
            "source_key": key,
            "dest_bucket": dest_bucket,
            "dest_key": dest_key
        })

    return images

async def run_single_image_workflow(client: Client, config: ImageProcessingConfig,
                                  image_config: Dict[str, str], task_queue: str,
                                  enhancement_prompt: str, show_progress: bool = False) -> Dict[str, Any]:
    """
    Run workflow for a single image.
    """
    source_location = S3Location(
        bucket=image_config['source_bucket'],
        key=image_config['source_key']
    )
    dest_location = S3Location(
        bucket=image_config['dest_bucket'],
        key=image_config['dest_key']
    )

    # Generate a unique workflow ID
    workflow_id = f"image-enhancement-{uuid.uuid4()}"

    if not show_progress:
        logger.info(f"Starting workflow for: s3://{source_location.bucket}/{source_location.key}")

    try:
        # Start the workflow
        handle = await client.start_workflow(
            ImageEnhancementWorkflow.run,
            args=[config, source_location, dest_location, enhancement_prompt],
            id=workflow_id,
            task_queue=task_queue,
            task_timeout=timedelta(seconds=60),
            execution_timeout=timedelta(minutes=20)
        )

        # Wait for workflow to complete and get result
        start_time = time.time()
        result = await handle.result()
        end_time = time.time()

        return {
            "workflow_id": workflow_id,
            "source": f"s3://{source_location.bucket}/{source_location.key}",
            "destination": f"s3://{dest_location.bucket}/{dest_location.key}",
            "status": "success",
            "result": result,
            "duration_seconds": round(end_time - start_time, 2)
        }

    except Exception as e:
        end_time = time.time()
        duration = round(end_time - start_time, 2) if 'start_time' in locals() else 0

        # Enhanced error logging with more context
        error_details = {
            "workflow_id": workflow_id,
            "source": f"{source_location.bucket}/{source_location.key}",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "duration_seconds": duration
        }

        logger.error(f"🚨 Workflow FAILED: {error_details['source']}")
        logger.error(f"   └─ Workflow ID: {workflow_id}")
        logger.error(f"   └─ Error Type: {error_details['error_type']}")
        logger.error(f"   └─ Error Message: {error_details['error_message']}")
        logger.error(f"   └─ Duration: {duration}s")

        # Log the full exception with stack trace in debug mode
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Full exception details for {workflow_id}:", exc_info=True)

        return {
            "workflow_id": workflow_id,
            "source": f"s3://{source_location.bucket}/{source_location.key}",
            "destination": f"s3://{dest_location.bucket}/{dest_location.key}",
            "status": "failed",
            "error": str(e),
            "error_type": type(e).__name__,
            "duration_seconds": duration
        }

async def run_batch_image_workflows(max_concurrent: int = 5, show_progress: bool = False):
    """
    Run image enhancement workflows for multiple images.
    """
    # Get Temporal server configuration
    temporal_address = os.getenv('TEMPORAL_ADDRESS', 'localhost:7233')
    temporal_namespace = os.getenv('TEMPORAL_NAMESPACE', 'default')
    task_queue = os.getenv('TEMPORAL_TASK_QUEUE', 'image-enhancement-queue')

    # Get batch processing configuration
    images_config = os.getenv('IMAGES_TO_PROCESS', '')
    enhancement_prompt = os.getenv('ENHANCEMENT_PROMPT',
                                 'Make this image more vibrant, increase clarity and sharpness, improve lighting')

    # Parse image list
    images = parse_image_list(images_config)

    if not images:
        # Fall back to single image configuration
        source_bucket = os.getenv('SOURCE_BUCKET', 'ricardotemporal')
        source_key = os.getenv('SOURCE_KEY', 'funny.png')
        dest_bucket = os.getenv('DEST_BUCKET', 'ricardotemporalprocessed')
        dest_key = os.getenv('DEST_KEY', 'enhanced_funny.png')

        images = [{
            "source_bucket": source_bucket,
            "source_key": source_key,
            "dest_bucket": dest_bucket,
            "dest_key": dest_key
        }]

    # AWS and OpenAI configuration
    config = ImageProcessingConfig(
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        aws_region=os.getenv('AWS_REGION', 'us-east-1'),
        openai_api_key=os.getenv('OPENAI_API_KEY')
    )

    if not show_progress:
        # Debug: Check if credentials are loaded
        logger.info(f"AWS Region: {config.aws_region}")
        logger.info(f"AWS Access Key ID loaded: {'Yes' if config.aws_access_key_id else 'No'}")
        logger.info(f"AWS Secret Key loaded: {'Yes' if config.aws_secret_access_key else 'No'}")
        logger.info(f"OpenAI API Key loaded: {'Yes' if config.openai_api_key else 'No'}")
        logger.info(f"Processing {len(images)} images with max concurrency: {max_concurrent}")

    # Progress bar setup
    overall_progress = None
    if show_progress:
        print(f"\n🚀 Starting batch image enhancement workflow")
        print(f"   Processing {len(images)} images with max concurrency: {max_concurrent}")
        print(f"   Estimated duration per image: ~40 seconds\n")

        overall_progress = tqdm(
            total=len(images),
            desc="Processing images",
            unit="images",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} images [{elapsed}<{remaining}]",
            ncols=100,
            dynamic_ncols=True
        )

    try:
        # Connect to Temporal server
        client = await Client.connect(
            temporal_address,
            namespace=temporal_namespace,
            retry_config=RetryConfig(
                max_interval_millis=5000,
                max_retries=3
            ),
            keep_alive_config=KeepAliveConfig(
                interval_millis=10000,
                timeout_millis=30000
            )
        )

        # Process images in batches
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        completed_count = 0

        async def process_with_semaphore(image_config, _):
            nonlocal completed_count
            async with semaphore:
                result = await run_single_image_workflow(
                    client, config, image_config, task_queue, enhancement_prompt, show_progress
                )

                # Update progress
                completed_count += 1
                if overall_progress:
                    overall_progress.update(1)
                    if result.get('status') == 'success':
                        overall_progress.set_description(f"Processing images (✅ {result['source'].split('/')[-1]})")
                    else:
                        overall_progress.set_description(f"Processing images (❌ {result['source'].split('/')[-1]})")
                elif not show_progress:
                    if result.get('status') == 'success':
                        logger.info(f"✅ {result['source']} -> {result['destination']} ({result['duration_seconds']}s)")
                    else:
                        logger.error(f"❌ {result['source']}: {result.get('error', 'Unknown error')}")
                    percent = int((completed_count/len(images))*100)
                    logger.info(f"Progress: {completed_count}/{len(images)} ({percent}%)")

                return result

        # Start all workflows
        if not show_progress:
            logger.info("Starting all workflows...")
        start_time = time.time()

        tasks = [process_with_semaphore(image_config, i) for i, image_config in enumerate(images)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        total_duration = round(end_time - start_time, 2)

        # Process results for summary
        successful = 0
        failed = 0

        for result in results:
            if isinstance(result, BaseException):
                failed += 1
            elif result.get('status') == 'success':
                successful += 1
            else:
                failed += 1

        # Close progress bar and show summary
        if overall_progress:
            overall_progress.close()
            print(f"\n✅ Successfully processed {successful}/{len(images)} images in {total_duration} seconds!")
            if failed > 0:
                print(f"   {failed} images failed to process")
            print(f"   Average time per image: {round(total_duration/len(images), 2)}s")
        else:
            # Summary
            logger.info(f"\n" + "="*80)
            logger.info(f"BATCH PROCESSING SUMMARY")
            logger.info(f"="*80)
            logger.info(f"Total images: {len(images)}")
            logger.info(f"Successful: {successful}")
            logger.info(f"Failed: {failed}")
            logger.info(f"Total duration: {total_duration}s")
            logger.info(f"Average per image: {round(total_duration/len(images), 2)}s")
            logger.info(f"="*80)

        return results

    except Exception as e:
        if overall_progress:
            overall_progress.close()
            print(f"\nError running batch workflows: {e}")
        else:
            logger.error(f"Error running batch workflows: {e}")
        raise

async def main():
    """
    Main function to run the workflows with command line argument support.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Batch Image Enhancement Workflows using Temporal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use with progress bars (default)
  python run_workflow.py

  # Use without progress bars (original logging)
  python run_workflow.py --no-progress

  # Process specific images with progress
  python run_workflow.py --images "image1.jpg,image2.png,folder/image3.jpeg"

  # Set concurrency and use progress bars
  python run_workflow.py --max-concurrent 10 --progress

Environment Variables:
  IMAGES_TO_PROCESS       - Comma-separated list of images or JSON array
  SOURCE_BUCKET           - Default source S3 bucket name (default: source-bucket)
  DEST_BUCKET            - Default destination S3 bucket name (default: dest-bucket)
  ENHANCEMENT_PROMPT     - Custom enhancement prompt
  MAX_CONCURRENT_WORKFLOWS - Max concurrent workflows (default: 5)
  TEMPORAL_ADDRESS       - Temporal server address (default: localhost:7233)
  TEMPORAL_NAMESPACE     - Temporal namespace (default: default)
  TEMPORAL_TASK_QUEUE    - Temporal task queue (default: image-enhancement-queue)
  AWS_ACCESS_KEY_ID      - AWS credentials
  AWS_SECRET_ACCESS_KEY  - AWS credentials
  AWS_REGION             - AWS region (default: us-east-1)
  OPENAI_API_KEY         - OpenAI API key
  LOG_LEVEL              - Logging level (default: INFO)
  TEMPORAL_DEBUG         - Enable Temporal debug logging (default: false)
        """
    )

    parser.add_argument('--images',
                       help='Comma-separated list of images to process')
    parser.add_argument('--max-concurrent',
                       type=int,
                       help='Maximum number of concurrent workflows')
    parser.add_argument('--enhancement-prompt',
                       help='Custom enhancement prompt')

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

    # Setup logging based on progress bar setting
    setup_logging(args.progress)

    # Override environment variables with command line arguments if provided
    if args.images:
        os.environ['IMAGES_TO_PROCESS'] = args.images
    if args.max_concurrent:
        os.environ['MAX_CONCURRENT_WORKFLOWS'] = str(args.max_concurrent)
    if args.enhancement_prompt:
        os.environ['ENHANCEMENT_PROMPT'] = args.enhancement_prompt

    try:
        # Get max concurrent workflows from environment or args
        max_concurrent = int(os.getenv('MAX_CONCURRENT_WORKFLOWS', '5'))

        results = await run_batch_image_workflows(max_concurrent, show_progress=args.progress)

        # Count successes and failures
        successful = sum(1 for r in results if isinstance(r, dict) and r.get('status') == 'success')
        total = len(results)

        if successful == total:
            if not args.progress:
                logger.info(f"All {total} images processed successfully!")
        else:
            failed = total - successful
            if not args.progress:
                logger.info(f"Processed {successful}/{total} images successfully ({failed} failed)")
            return 1

        return 0

    except Exception as e:
        if not args.progress:
            logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))


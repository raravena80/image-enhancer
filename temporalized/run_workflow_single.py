#!/usr/bin/env python3

"""
This script runs a single image enhancement workflow using Temporal.

It loads configuration from environment variables, connects to the Temporal
server, and executes the workflow for "one" image, suitable for testing or single-job runs.
"""
import asyncio
import logging
from temporalio.client import Client
from workflows import ImageEnhancementWorkflow
from activities import ImageProcessingConfig, S3Location
import os
from dotenv import load_dotenv
import uuid
import argparse
import time
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
        # Also quiet temporal logging
        logging.getLogger('temporalio').setLevel(logging.WARNING)
        logging.getLogger('grpc').setLevel(logging.WARNING)
        # Set the main module logger level as well
        logging.getLogger(__name__).setLevel(logging.WARNING)
    else:
        # Normal logging mode
        log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            force=True
        )

async def run_image_enhancement_workflow(show_progress=False):
    """
    Start an image enhancement workflow execution.
    """
    # Get Temporal server configuration
    temporal_address = os.getenv('TEMPORAL_ADDRESS', 'localhost:7233')
    temporal_namespace = os.getenv('TEMPORAL_NAMESPACE', 'default')
    task_queue = os.getenv('TEMPORAL_TASK_QUEUE', 'image-enhancement-queue')

    # Get workflow configuration from environment
    source_bucket = os.getenv('SOURCE_BUCKET', 'ricardotemporal')
    source_key = os.getenv('SOURCE_KEY', 'funny.png')
    dest_bucket = os.getenv('DEST_BUCKET', 'ricardotemporalprocessed')
    dest_key = os.getenv('DEST_KEY', 'enhanced_funny.png')
    enhancement_prompt = os.getenv('ENHANCEMENT_PROMPT',
                                 'Make this image more vibrant, increase clarity and sharpness, improve lighting')

    # AWS and OpenAI configuration
    config = ImageProcessingConfig(
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        aws_region=os.getenv('AWS_REGION', 'us-east-1'),
        openai_api_key=os.getenv('OPENAI_API_KEY'),
        openai_model=os.getenv('OPENAI_MODEL', 'gpt-image-1'),
        openai_size=os.getenv('OPENAI_SIZE', '1024x1024')
    )

    # Debug: Check if credentials are loaded
    if not show_progress:
        logger.info(f"AWS Region: {config.aws_region}")
        logger.info(f"AWS Access Key ID loaded: {'Yes' if config.aws_access_key_id else 'No'}")
        logger.info(f"AWS Secret Key loaded: {'Yes' if config.aws_secret_access_key else 'No'}")
        logger.info(f"OpenAI API Key loaded: {'Yes' if config.openai_api_key else 'No'}")

    source_location = S3Location(bucket=source_bucket, key=source_key)
    dest_location = S3Location(bucket=dest_bucket, key=dest_key)

    if not show_progress:
        logger.info(f"Connecting to Temporal server at {temporal_address}")
        logger.info(f"Processing: s3://{source_bucket}/{source_key} -> s3://{dest_bucket}/{dest_key}")

    # Progress bar setup
    progress_bar = None
    if show_progress:
        print(f"\n🚀 Starting image enhancement workflow")
        print(f"   Source: s3://{source_bucket}/{source_key}")
        print(f"   Destination: s3://{dest_bucket}/{dest_key}")
        print(f"   Estimated duration: ~40 seconds\n")

        progress_bar = tqdm(
            total=100,
            desc="Processing image",
            unit="%",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
            ncols=100,
            dynamic_ncols=True
        )

    try:
        # Connect to Temporal server
        client = await Client.connect(temporal_address, namespace=temporal_namespace)

        if progress_bar:
            progress_bar.update(10)
            progress_bar.set_description("Connected to Temporal")

        # Generate a unique workflow ID
        workflow_id = f"image-enhancement-{uuid.uuid4()}"

        if not show_progress:
            logger.info(f"Starting workflow with ID: {workflow_id}")

        # Start the workflow
        handle = await client.start_workflow(
            ImageEnhancementWorkflow.run,
            args=[config, source_location, dest_location, enhancement_prompt],
            id=workflow_id,
            task_queue=task_queue,
            task_timeout=timedelta(seconds=60),
            execution_timeout=timedelta(minutes=20)
        )

        if progress_bar:
            progress_bar.update(10)
            progress_bar.set_description("Workflow started, processing image")

        if not show_progress:
            logger.info(f"Workflow started. Workflow ID: {handle.id}")
            logger.info("Waiting for workflow to complete...")

        # Simulate progress while waiting for workflow completion
        start_time = time.time()
        if progress_bar:
            # Start background task to simulate progress
            async def simulate_progress():
                await asyncio.sleep(2)
                progress_bar.update(20)
                progress_bar.set_description("Downloading image from S3")

                await asyncio.sleep(5)
                progress_bar.update(10)
                progress_bar.set_description("Enhancing image with OpenAI")

                # Simulate the long enhancement process
                for _ in range(6):
                    await asyncio.sleep(4)
                    if progress_bar.n < 90:
                        progress_bar.update(8)

                await asyncio.sleep(3)
                progress_bar.update(5)
                progress_bar.set_description("Uploading enhanced image to S3")

            # Start progress simulation
            asyncio.create_task(simulate_progress())

        # Wait for workflow to complete and get result
        result = await handle.result()

        end_time = time.time()
        duration = round(end_time - start_time, 2)

        if progress_bar:
            # Ensure progress is at 100%
            progress_bar.n = 100
            progress_bar.set_description("Complete!")
            progress_bar.refresh()
            progress_bar.close()

            print(f"\n✅ Successfully processed image in {duration} seconds!")
            print(f"   Source: s3://{source_bucket}/{source_key}")
            print(f"   Destination: s3://{dest_bucket}/{dest_key}")
        else:
            logger.info(f"Workflow completed successfully!")
            logger.info(f"Result: {result}")

        return result

    except Exception as e:
        if progress_bar:
            progress_bar.close()
            print(f"\nError during workflow execution: {e}")
        else:
            logger.error(f"Error running workflow: {e}")
        raise

async def main():
    """
    Main function to run the workflow with command line argument support.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Single Image Enhancement Workflow using Temporal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use with progress bars (default)
  python run_workflow_single.py

  # Use without progress bars (original logging)
  python run_workflow_single.py --no-progress

  # Override configuration via command line
  python run_workflow_single.py --source-bucket my-bucket --source-key image.jpg --dest-bucket output --dest-key enhanced.jpg

Environment Variables:
   SOURCE_BUCKET          - Source S3 bucket name (default: ricardotemporal)
   SOURCE_KEY             - Source object key/path (default: funny.png)
   DEST_BUCKET            - Destination S3 bucket name (default: ricardotemporalprocessed)
   DEST_KEY               - Destination object key/path (default: enhanced_funny.png)
   ENHANCEMENT_PROMPT     - Custom enhancement prompt
   TEMPORAL_ADDRESS       - Temporal server address (default: localhost:7233)
   TEMPORAL_NAMESPACE     - Temporal namespace (default: default)
   TEMPORAL_TASK_QUEUE    - Temporal task queue (default: image-enhancement-queue)
   AWS_ACCESS_KEY_ID      - AWS credentials
   AWS_SECRET_ACCESS_KEY  - AWS credentials
   AWS_REGION             - AWS region (default: us-east-1)
   OPENAI_API_KEY         - OpenAI API key
   OPENAI_MODEL           - OpenAI image model (default: gpt-image-1)
   OPENAI_SIZE            - Image size for OpenAI generation (default: 1024x1024)
   LOG_LEVEL              - Logging level (default: INFO)        """
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
    parser.add_argument('--openai-model',
                       help='OpenAI image model to use (default: gpt-image-1)')
    parser.add_argument('--openai-size',
                       help='Image size for OpenAI generation (default: 1024x1024)')

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
    if args.source_bucket:
        os.environ['SOURCE_BUCKET'] = args.source_bucket
    if args.source_key:
        os.environ['SOURCE_KEY'] = args.source_key
    if args.dest_bucket:
        os.environ['DEST_BUCKET'] = args.dest_bucket
    if args.dest_key:
        os.environ['DEST_KEY'] = args.dest_key
    if args.enhancement_prompt:
        os.environ['ENHANCEMENT_PROMPT'] = args.enhancement_prompt
    if args.openai_model:
        os.environ['OPENAI_MODEL'] = args.openai_model
    if args.openai_size:
        os.environ['OPENAI_SIZE'] = args.openai_size

    try:
        result = await run_image_enhancement_workflow(show_progress=args.progress)
        if not args.progress:
            logger.info(f"Success: {result}")
        return 0
    except Exception as e:
        if not args.progress:
            logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))

"""
This script starts a Temporal worker for image enhancement workflows.

It connects to a Temporal server, registers the workflow and activities, and runs the worker to process image enhancement tasks using AWS S3 and OpenAI.
"""
import asyncio
import logging
from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker
from workflows import ImageEnhancementWorkflow
from activities import (
    download_image_from_s3,
    enhance_image_with_openai,
    upload_image_to_s3,
    cleanup_temp_file
)
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """
    Start the Temporal worker to process image enhancement workflows.
    """
    # Get Temporal server address from environment or use default
    temporal_address = os.getenv('TEMPORAL_ADDRESS', 'localhost:7233')
    temporal_namespace = os.getenv('TEMPORAL_NAMESPACE', 'default')
    task_queue = os.getenv('TEMPORAL_TASK_QUEUE', 'image-enhancement-queue')

    logger.info(f"Connecting to Temporal server at {temporal_address}")
    logger.info(f"Using namespace: {temporal_namespace}")
    logger.info(f"Using task queue: {task_queue}")

    try:
        # Connect to Temporal server
        client = await Client.connect(temporal_address, namespace=temporal_namespace)

        # Create worker
        worker = Worker(
            client,
            task_queue=task_queue,
            workflows=[ImageEnhancementWorkflow],
            activities=[
                download_image_from_s3,
                enhance_image_with_openai,
                upload_image_to_s3,
                cleanup_temp_file
            ],
        )

        logger.info("Starting worker...")
        logger.info("Worker is ready to process image enhancement workflows")

        # Run the worker
        await worker.run()

    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Error running worker: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())

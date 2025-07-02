import asyncio
import logging
from temporalio.client import Client
from workflows import ImageEnhancementWorkflow
from activities import ImageProcessingConfig, S3Location
import os
from dotenv import load_dotenv
import uuid
import json
from typing import List, Dict, Any
from concurrent.futures import as_completed
import time

# Load environment variables
load_dotenv()

# Configure logging
log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
                                  enhancement_prompt: str) -> Dict[str, Any]:
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
    
    logger.info(f"Starting workflow for: s3://{source_location.bucket}/{source_location.key}")
    
    try:
        # Start the workflow
        handle = await client.start_workflow(
            ImageEnhancementWorkflow.run,
            args=[config, source_location, dest_location, enhancement_prompt],
            id=workflow_id,
            task_queue=task_queue,
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
        logger.error(f"Error processing {source_location.bucket}/{source_location.key}: {e}")
        return {
            "workflow_id": workflow_id,
            "source": f"s3://{source_location.bucket}/{source_location.key}",
            "destination": f"s3://{dest_location.bucket}/{dest_location.key}",
            "status": "failed",
            "error": str(e),
            "duration_seconds": 0
        }

async def run_batch_image_workflows(max_concurrent: int = 5):
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
    
    # Debug: Check if credentials are loaded
    logger.info(f"AWS Region: {config.aws_region}")
    logger.info(f"AWS Access Key ID loaded: {'Yes' if config.aws_access_key_id else 'No'}")
    logger.info(f"AWS Secret Key loaded: {'Yes' if config.aws_secret_access_key else 'No'}")
    logger.info(f"OpenAI API Key loaded: {'Yes' if config.openai_api_key else 'No'}")
    logger.info(f"Processing {len(images)} images with max concurrency: {max_concurrent}")
    
    try:
        # Connect to Temporal server
        client = await Client.connect(temporal_address, namespace=temporal_namespace)
        
        # Process images in batches
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(image_config):
            async with semaphore:
                return await run_single_image_workflow(
                    client, config, image_config, task_queue, enhancement_prompt
                )
        
        # Start all workflows
        logger.info("Starting all workflows...")
        start_time = time.time()
        
        tasks = [process_with_semaphore(image_config) for image_config in images]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_duration = round(end_time - start_time, 2)
        
        # Process results
        successful = 0
        failed = 0
        
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                logger.error(f"Workflow {i+1} failed with exception: {result}")
                failed += 1
            elif result.get('status') == 'success':
                logger.info(f"✅ {result['source']} -> {result['destination']} ({result['duration_seconds']}s)")
                successful += 1
            else:
                logger.error(f"❌ {result['source']}: {result.get('error', 'Unknown error')}")
                failed += 1
        
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
        logger.error(f"Error running batch workflows: {e}")
        raise

async def main():
    """
    Main function to run the workflows.
    """
    try:
        # Get max concurrent workflows from environment
        max_concurrent = int(os.getenv('MAX_CONCURRENT_WORKFLOWS', '5'))
        
        results = await run_batch_image_workflows(max_concurrent)
        
        # Count successes and failures
        successful = sum(1 for r in results if isinstance(r, dict) and r.get('status') == 'success')
        total = len(results)
        
        if successful == total:
            print(f"\n🎉 All {total} images processed successfully!")
        else:
            failed = total - successful
            print(f"\n⚠️  Processed {successful}/{total} images successfully ({failed} failed)")
            exit(1)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())


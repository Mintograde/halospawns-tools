import json
from pprint import pprint

import boto3
import time
import os
import logging
from botocore.exceptions import ClientError

from convert_map import map_to_glb

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

QUEUE_URL = os.environ.get('SQS_QUEUE_URL', 'https://sqs.us-east-1.amazonaws.com/283279960672/maps-processing-queue')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
AWS_PROFILE = os.environ.get('AWS_PROFILE', 'halospawns-dev')
BASE_DIRECTORY = os.environ.get('BASE_DIRECTORY', r'L:\ce')
OUTPUT_DIRECTORY = os.environ.get('OUTPUT_DIRECTORY', r'L:\ce\output/')
INPUT_DIRECTORY = os.environ.get('INPUT_DIRECTORY', r'L:\ce\input/')

WAIT_TIME_SECONDS = 20
MAX_MESSAGES = 10


def download_from_s3(s3_bucket, s3_key):
    session = boto3.session.Session(profile_name=AWS_PROFILE)
    s3 = session.client('s3', region_name=AWS_REGION)
    local_file = os.path.join(INPUT_DIRECTORY, os.path.basename(s3_key))
    os.makedirs(INPUT_DIRECTORY, exist_ok=True)
    try:
        logging.info(f"Downloading {s3_bucket}/{s3_key} to {local_file}")
        s3.download_file(s3_bucket, s3_key, local_file)
        logging.info("Download complete")
        return local_file
    except ClientError as e:
        logging.error(f"Error downloading file from S3: {e}")
        raise


def upload_to_s3(filename, s3_bucket, s3_key):
    session = boto3.session.Session(profile_name=AWS_PROFILE)
    s3 = session.client('s3', region_name=AWS_REGION)
    try:
        logging.info(f"Uploading {filename} to {s3_bucket}/{s3_key}")
        s3.upload_file(filename, s3_bucket, s3_key)
        logging.info("Upload complete")
        return s3_key
    except ClientError as e:
        logging.error(f"Error uploading file to S3: {e}")
        raise


def process_message(message):
    """
    Your custom logic to process a single message.
    If this function raises an exception, the message will not be deleted
    and will become visible in the queue again after the visibility timeout.
    """
    logging.info(f"Received message ID: {message['MessageId']}")
    logging.info(f"Message Body: {message['Body']}")
    inner_message = json.loads(json.loads(message['Body'])['Message'])
    pprint(inner_message)
    for record in inner_message['Records']:
        s3_bucket = record['s3']['bucket']['name']
        s3_key = record['s3']['object']['key']
        print(f"Processing {s3_bucket}/{s3_key}")
        file_path = download_from_s3(s3_bucket, s3_key)
        file_basename = os.path.basename(file_path)
        results = map_to_glb(file_path, BASE_DIRECTORY, OUTPUT_DIRECTORY)
        upload_to_s3(results['glb'], s3_bucket, f'maps/processed/{results["map_name"]}_{file_basename}.glb')
        upload_to_s3(results['meta'], s3_bucket, f'maps/processed/{results["map_name"]}_{file_basename}.json')
        # TODO: move original upload from maps/unprocessed to maps/originals (and rename to match upload)
        # TODO: notify api to update database

    logging.info(f"Finished processing message {message['MessageId']}")


def main():
    """Main function to poll SQS and process messages."""
    if not QUEUE_URL:
        logging.error("SQS_QUEUE_URL environment variable not set.")
        return

    session = boto3.session.Session(profile_name=AWS_PROFILE)
    sqs = session.client('sqs', region_name=AWS_REGION)

    logging.info(f"Worker starting... Polling SQS queue: {QUEUE_URL}")

    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=MAX_MESSAGES,
                WaitTimeSeconds=WAIT_TIME_SECONDS,
                VisibilityTimeout=300
            )

            messages = response.get('Messages', [])

            if not messages:
                logging.debug("No messages received. Polling again...")
                continue

            for message in messages:
                try:
                    process_message(message)

                    sqs.delete_message(
                        QueueUrl=QUEUE_URL,
                        ReceiptHandle=message['ReceiptHandle']
                    )
                    logging.info(f"Deleted message {message['MessageId']} from queue.")

                except Exception as e:
                    logging.error(f"Error processing message {message['MessageId']}: {e}", exc_info=True)

        except ClientError as e:
            logging.error(f"AWS Boto3 client error: {e}", exc_info=True)
            time.sleep(15)
        except Exception as e:
            logging.critical(f"An unexpected error occurred in the main loop: {e}", exc_info=True)
            time.sleep(15)


if __name__ == '__main__':
    main()
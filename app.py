import json
import shutil
import sys
import traceback
from pprint import pprint

import boto3
import os
import urllib.parse

from convert_map import map_to_glb

s3 = boto3.client('s3')

try:
    print(f"Python Version: {sys.version}")
    print(f"Python Executable: {sys.executable}")
    for var in [
        'PATH',
        'LAMBDA_TASK_ROOT',
        'DOTNET_ROOT',
        'AETHER_EXECUTABLE_PATH',
        'BLENDER_EXECUTABLE_PATH',
        'CE_PATH',
        'PYTHONPATH',
        'AWS_LAMBDA_FUNCTION_NAME',
        'AWS_REGION'
    ]:
        print(f"{var:<25} = {os.environ.get(var, 'NOT SET')}")
    print("-" * 20)
except Exception as e:
    print(f"An error occurred during diagnostic logging: {e}")
    traceback.print_exc()
print("=" * 50)


def handler(event, context):
    results = []

    # print("Received event:")
    # pprint(event)
    # print('-' * 20)

    for record in event.get("Records", []):
        try:
            sns_notification = json.loads(record["body"])
            print(f'SNS message id: {sns_notification.get("MessageId", "UNKNOWN")}:')
            print(f'SQS message id: {record.get("messageId", "UNKNOWN")}')
            s3_event = json.loads(sns_notification["Message"])
            # print('s3 event:')
            # pprint(s3_event)
            for s3_record in s3_event.get("Records", []):
                bucket = s3_record["s3"]["bucket"]["name"]
                key = urllib.parse.unquote_plus(s3_record["s3"]["object"]["key"])
                event_name = s3_record["eventName"]
                print(f'Handling {event_name} notification for {bucket}/{key}')

                base_directory = "/tmp/ce"
                output_directory = f"{base_directory}/output"
                input_directory = f"{base_directory}/input"
                map_file_path = f"{input_directory}/{os.path.basename(key)}"

                os.makedirs(input_directory, exist_ok=True)
                os.makedirs(output_directory, exist_ok=True)

                print(f"Downloading s3://{bucket}/{key} to {map_file_path}")
                s3.download_file(bucket, key, map_file_path)

                try:
                    result_path = map_to_glb(map_file_path, base_directory, output_directory)
                except Exception as e:
                    print("An error occurred:")
                    traceback.print_exc(file=sys.stdout)
                else:

                    pprint(result_path)

                    print(f"Uploading to s3://{bucket}/maps/processed/{os.path.basename(result_path['glb'])}")
                    s3.upload_file(result_path["glb"], bucket, f'maps/processed/{os.path.basename(result_path["glb"])}')
                    print(f"Uploading to s3://{bucket}/maps/processed/{os.path.basename(result_path['blend'])}")
                    s3.upload_file(result_path["blend"], bucket, f'maps/processed/{os.path.basename(result_path["blend"])}')

                    results.append({
                        "input": f"s3://{bucket}/{key}",
                        "output": result_path,
                        "status": "success"
                    })

                    # base_directory_to_zip = "/tmp/ce"
                    # print(f"Zipping contents of {base_directory_to_zip} for debugging...")
                    # archive_name = f"ce_debug_archive_{context.aws_request_id}"
                    # archive_path_base = f"/tmp/{archive_name}"
                    # archive_file_path = None
                    # try:
                    #     archive_file_path = shutil.make_archive(
                    #         base_name=archive_path_base,
                    #         format='zip',
                    #         root_dir=base_directory_to_zip
                    #     )
                    #     s3_key = f"maps/processed/{os.path.basename(archive_file_path)}"
                    #     print(f"Uploading debug archive to s3://{bucket}/{s3_key}")
                    #     s3.upload_file(archive_file_path, bucket, s3_key)
                    #     print("Debug archive upload complete.")
                    # except Exception as e:
                    #     print(f"Failed to create or upload debug archive: {e}")
                    #     traceback.print_exc(file=sys.stdout)
                    # finally:
                    #     if archive_file_path and os.path.exists(archive_file_path):
                    #         os.remove(archive_file_path)
                    #         print(f"Removed temporary archive: {archive_file_path}")

        except Exception as e:
            print(f"An error occurred processing SNS message: {e}")
            traceback.print_exc()
            results.append({
                "input": record.get("body"),
                "error": str(e),
                "status": "failure"
            })

    return {
        "statusCode": 200,
        "body": json.dumps(results, default=str)
    }

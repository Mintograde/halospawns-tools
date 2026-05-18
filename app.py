import hashlib
import hmac
import json
import math
import os
import posixpath
import re
import shutil
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import boto3
from conversion_runtime import run_conversion
from local_io_mode import process_local_event, resolve_io_mode

S3 = None
SECRETS = None
SECRET_CACHE = {}
MAX_SPAWN_POINTS = 512
PROCESSOR_NAME = "halospawns-tools"

UUID_PATTERN = re.compile(
    r"(?P<upload_id>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12})"
)


def _redacted_env(name):
    value = os.environ.get(name)
    if value is None:
        return "NOT SET"
    if name.endswith("SECRET_ID") or "SECRET" in name:
        return "SET"
    return value


try:
    print(f"Python Version: {sys.version}")
    print(f"Python Executable: {sys.executable}")
    for var in [
        "PATH",
        "LAMBDA_TASK_ROOT",
        "DOTNET_ROOT",
        "AETHER_EXECUTABLE_PATH",
        "BLENDER_EXECUTABLE_PATH",
        "CE_PATH",
        "PYTHONPATH",
        "AWS_LAMBDA_FUNCTION_NAME",
        "AWS_REGION",
        "APP_API_BASE_URL",
        "APP_API_TRUSTED_CLIENT_NAME",
        "APP_API_TRUSTED_CLIENT_HMAC_SECRET_ID",
        "APP_API_MAP_FINALIZATION_PATH",
    ]:
        print(f"{var:<45} = {_redacted_env(var)}")
    print("-" * 20)
except Exception as e:
    print(f"An error occurred during diagnostic logging: {e}")
    traceback.print_exc()
print("=" * 50)


class MapProcessingError(Exception):
    """Base class for retryable map processing failures."""


class NonRetryableMapError(MapProcessingError):
    """The uploaded map cannot be processed by retrying the same object."""

    def __init__(self, message, *, status="failed"):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class S3MapObject:
    bucket: str
    key: str
    event_name: str | None
    sqs_message_id: str


@dataclass(frozen=True)
class DownloadedMap:
    path: Path
    content_type: str | None
    size_bytes: int
    sha256: str
    metadata: dict[str, str]


def _s3_client():
    global S3
    if S3 is None:
        S3 = boto3.client("s3")
    return S3


def _secrets_client():
    global SECRETS
    if SECRETS is None:
        SECRETS = boto3.client("secretsmanager")
    return SECRETS


def _as_dict(event):
    return event if isinstance(event, dict) else {}


def _process_s3_event(event, results):
    failures = []

    for record in event.get("Records", []):
        sqs_message_id = str(record.get("messageId") or record.get("messageID") or "")
        try:
            map_objects = _map_objects_from_record(record, sqs_message_id)
            for map_object in map_objects:
                result = _process_map_object(map_object)
                if result is not None:
                    results.append(result)
        except NonRetryableMapError as e:
            print(f"Non-retryable map event failure: {e}")
            traceback.print_exc()
            results.append(
                {
                    "input": record.get("body"),
                    "error": str(e),
                    "status": "failure",
                    "retryable": False,
                }
            )
        except Exception as e:
            print(f"Retryable map event failure: {e}")
            traceback.print_exc()
            results.append(
                {
                    "input": record.get("body"),
                    "error": str(e),
                    "status": "failure",
                    "retryable": True,
                }
            )
            failures.append({"itemIdentifier": sqs_message_id or str(len(failures))})

    if failures and not _bool_env("REPORT_BATCH_ITEM_FAILURES", False):
        raise MapProcessingError(f"{len(failures)} SQS message(s) failed")

    return failures


def _process_map_object(map_object):
    settings = _settings()
    if not map_object.key.startswith(settings["unprocessed_prefix"]):
        print(f"Skipping non-map-unprocessed object: {map_object.key}")
        return {
            "input": f"s3://{map_object.bucket}/{map_object.key}",
            "status": "skipped",
            "reason": "outside map unprocessed prefix",
        }

    upload_id = _upload_id_from_key(map_object.key)
    base_directory = Path(settings["base_directory"]) / upload_id
    input_directory = base_directory / "input"
    output_directory = base_directory / "output"
    input_directory.mkdir(parents=True, exist_ok=True)
    output_directory.mkdir(parents=True, exist_ok=True)
    map_file_path = input_directory / posixpath.basename(map_object.key)

    try:
        _send_upload_status(
            upload_id,
            "processing",
            metadata={
                "s3": {
                    "bucket": map_object.bucket,
                    "key": map_object.key,
                    "event_name": map_object.event_name,
                },
            },
        )

        downloaded = _download_map(map_object, map_file_path)
        metadata_upload_id = downloaded.metadata.get("upload-id")
        if metadata_upload_id and metadata_upload_id.lower() != upload_id:
            raise NonRetryableMapError(
                "S3 object metadata upload-id did not match the upload ID in the object key",
                status="rejected",
            )

        _validate_expected_upload(downloaded)
        result_path = run_conversion(
            str(downloaded.path),
            str(base_directory),
            str(output_directory),
        )
        if not result_path:
            raise NonRetryableMapError("map_to_glb failed; see logs")

        processed_keys = _upload_processed_outputs(
            bucket=map_object.bucket,
            upload_id=upload_id,
            source_key=map_object.key,
            result_path=result_path,
            processed_prefix=settings["processed_prefix"],
        )
        _copy_object(map_object.bucket, map_object.key, processed_keys["original_map"])

        _finalize_map_upload(
            upload_id,
            bucket=map_object.bucket,
            source_key=map_object.key,
            downloaded=downloaded,
            result_path=result_path,
            processed_keys=processed_keys,
        )

        _delete_object(map_object.bucket, map_object.key)
        print(
            f"Processed map upload {upload_id} from s3://{map_object.bucket}/{map_object.key} "
            f"to s3://{map_object.bucket}/{processed_keys['original_map']} "
            "and finalized catalog ingest"
        )
        return {
            "input": f"s3://{map_object.bucket}/{map_object.key}",
            "output": {
                name: f"s3://{map_object.bucket}/{key}"
                for name, key in processed_keys.items()
            },
            "status": "success",
            "upload_id": upload_id,
        }

    except NonRetryableMapError as e:
        print(f"Map upload {upload_id} is not processable: {e}")
        failed_key = _processed_key(
            map_object.key,
            unprocessed_prefix=settings["unprocessed_prefix"],
            processed_prefix=settings["failed_prefix"],
        )
        _send_upload_status(
            upload_id,
            e.status,
            processing_error=str(e),
            metadata={
                "s3": {
                    "bucket": map_object.bucket,
                    "key": map_object.key,
                    "failed_key": failed_key,
                    "event_name": map_object.event_name,
                },
            },
        )
        _copy_object(map_object.bucket, map_object.key, failed_key)
        _delete_object(map_object.bucket, map_object.key)
        return {
            "input": f"s3://{map_object.bucket}/{map_object.key}",
            "output": f"s3://{map_object.bucket}/{failed_key}",
            "status": e.status,
            "error": str(e),
            "upload_id": upload_id,
        }
    finally:
        shutil.rmtree(base_directory, ignore_errors=True)


def _map_objects_from_record(record, sqs_message_id):
    payload = _record_payload(record)
    map_objects = []

    for s3_record in payload.get("Records", []):
        s3_data = s3_record.get("s3") or {}
        bucket = (s3_data.get("bucket") or {}).get("name")
        key = (s3_data.get("object") or {}).get("key")
        if not bucket or not key:
            continue
        map_objects.append(
            S3MapObject(
                bucket=str(bucket),
                key=urllib.parse.unquote_plus(str(key)),
                event_name=s3_record.get("eventName"),
                sqs_message_id=sqs_message_id,
            )
        )

    return map_objects


def _record_payload(record):
    body = record.get("body")
    if body is None and "s3" in record:
        return {"Records": [record]}

    try:
        payload = json.loads(str(body))
    except json.JSONDecodeError as error:
        raise NonRetryableMapError("SQS record body was not valid JSON") from error

    if isinstance(payload, dict) and isinstance(payload.get("Message"), str):
        try:
            message = json.loads(payload["Message"])
        except json.JSONDecodeError as error:
            raise NonRetryableMapError("SNS message was not valid JSON") from error
        if isinstance(message, dict):
            return message

    if isinstance(payload, dict):
        return payload

    raise NonRetryableMapError("SQS record body did not contain an S3 event")


def _download_map(map_object, destination):
    response = _s3_client().get_object(Bucket=map_object.bucket, Key=map_object.key)
    body = response["Body"]
    hasher = hashlib.sha256()
    size_bytes = 0

    with destination.open("wb") as output:
        for chunk in iter(lambda: body.read(1024 * 1024), b""):
            if not chunk:
                break
            hasher.update(chunk)
            size_bytes += len(chunk)
            output.write(chunk)

    metadata = {
        str(key).lower(): str(value)
        for key, value in (response.get("Metadata") or {}).items()
    }
    return DownloadedMap(
        path=destination,
        content_type=response.get("ContentType"),
        size_bytes=size_bytes,
        sha256=hasher.hexdigest(),
        metadata=metadata,
    )


def _validate_expected_upload(downloaded):
    expected_sha256 = downloaded.metadata.get("expected-sha256")
    if expected_sha256 and expected_sha256.lower() != downloaded.sha256:
        raise NonRetryableMapError(
            "Uploaded map SHA-256 did not match the presigned upload metadata",
            status="rejected",
        )

    expected_size_bytes = downloaded.metadata.get("expected-size-bytes")
    if expected_size_bytes:
        try:
            expected_size = int(expected_size_bytes)
        except ValueError as error:
            raise NonRetryableMapError(
                "Uploaded map expected-size-bytes metadata was invalid",
                status="rejected",
            ) from error
        if expected_size != downloaded.size_bytes:
            raise NonRetryableMapError(
                "Uploaded map size did not match the presigned upload metadata",
                status="rejected",
            )


def _upload_processed_outputs(*, bucket, upload_id, source_key, result_path, processed_prefix):
    map_name = _map_name_from_result(result_path, source_key)
    prefix = f"{processed_prefix}{upload_id}/"
    keys = {
        "original_map": f"{prefix}{posixpath.basename(source_key)}",
        "glb": f"{prefix}{map_name}.glb",
        "metadata": f"{prefix}{map_name}.json",
    }
    if result_path.get("blend"):
        keys["blend"] = f"{prefix}{map_name}.blend"

    _upload_file(result_path["glb"], bucket, keys["glb"], "model/gltf-binary")
    _upload_file(result_path["meta"], bucket, keys["metadata"], "application/json")
    if "blend" in keys:
        _upload_file(result_path["blend"], bucket, keys["blend"], "application/octet-stream")
    return keys


def _finalize_map_upload(upload_id, *, bucket, source_key, downloaded, result_path, processed_keys):
    try:
        return _call_app_api(
            "POST",
            _settings()["map_finalization_path"],
            _map_finalization_payload(
                upload_id=upload_id,
                bucket=bucket,
                source_key=source_key,
                downloaded=downloaded,
                result_path=result_path,
                processed_keys=processed_keys,
            ),
        )
    except Exception as error:
        print(f"Map finalization failed for upload {upload_id}: {error}")
        _report_finalization_failure(
            upload_id,
            bucket=bucket,
            source_key=source_key,
            downloaded=downloaded,
            processed_keys=processed_keys,
            error=error,
        )
        raise


def _map_finalization_payload(
    *,
    upload_id,
    bucket,
    source_key,
    downloaded,
    result_path,
    processed_keys,
):
    map_name = _map_name_from_result(result_path, source_key)
    original_file_metadata = {
        "original_s3_key": source_key,
    }
    original_filename = downloaded.metadata.get("original-filename")
    if original_filename:
        original_file_metadata["original_filename"] = original_filename

    artifacts = {
        "glb": {
            "s3_bucket": bucket,
            "s3_key": processed_keys["glb"],
            "file_role": "processed",
            "content_type": "model/gltf-binary",
        },
        "metadata": {
            "s3_bucket": bucket,
            "s3_key": processed_keys["metadata"],
            "file_role": "metadata",
            "content_type": "application/json",
        },
    }
    if processed_keys.get("blend"):
        artifacts["blend"] = {
            "s3_bucket": bucket,
            "s3_key": processed_keys["blend"],
            "content_type": "application/octet-stream",
        }

    payload = {
        "upload_id": upload_id,
        "source_external_id": upload_id,
        "map": {
            "map_name": map_name,
            "display_name": _display_name_for_map(
                map_name=map_name,
                source_key=source_key,
                downloaded_metadata=downloaded.metadata,
            ),
            "engine_name": map_name,
            "metadata": {},
        },
        "original_file": {
            "s3_bucket": bucket,
            "s3_key": processed_keys["original_map"],
            "file_role": "original",
            "content_type": downloaded.content_type or "application/octet-stream",
            "size_bytes": downloaded.size_bytes,
            "sha256": downloaded.sha256,
            "metadata": original_file_metadata,
        },
        "artifacts": artifacts,
        "metadata": {
            "processor_runtime": {
                "name": PROCESSOR_NAME,
            },
        },
    }
    spawn_points = _map_spawn_points_from_metadata(result_path)
    if spawn_points:
        payload["spawn_points"] = spawn_points
        payload["spawn_source"] = {
            "path": "$.spawns",
            "extractor": PROCESSOR_NAME,
        }
    return payload


def _map_spawn_points_from_metadata(result_path):
    metadata_path = result_path.get("meta")
    if not metadata_path:
        return None

    try:
        with Path(metadata_path).open("r", encoding="utf-8") as metadata_file:
            metadata = json.load(metadata_file)
    except Exception as error:
        print(f"Map spawn extraction skipped; metadata JSON could not be read: {error}")
        return None

    return _spawn_points_from_records(metadata.get("spawns"))


def _spawn_points_from_records(records):
    if not isinstance(records, list):
        return None

    points = []
    skipped = 0
    for record in records:
        point = _spawn_point_from_record(record)
        if point is None:
            skipped += 1
            continue
        points.append(point)
        if len(points) >= MAX_SPAWN_POINTS:
            break

    if skipped:
        print(f"Skipped {skipped} spawn record(s) without finite x/y/z coordinates")
    if len(records) > MAX_SPAWN_POINTS:
        print(f"Truncated spawn records from {len(records)} to {MAX_SPAWN_POINTS}")
    return points or None


def _spawn_point_from_record(record):
    try:
        if isinstance(record, dict):
            if all(axis in record for axis in ("x", "y", "z")):
                return _finite_spawn_point(record["x"], record["y"], record["z"])
            for key in ("position", "translation", "origin", "location"):
                nested = record.get(key)
                if isinstance(nested, dict) and all(axis in nested for axis in ("x", "y", "z")):
                    return _finite_spawn_point(nested["x"], nested["y"], nested["z"])
                if isinstance(nested, (list, tuple)) and len(nested) >= 3:
                    return _finite_spawn_point(nested[0], nested[1], nested[2])
        if isinstance(record, (list, tuple)) and len(record) >= 3:
            return _finite_spawn_point(record[0], record[1], record[2])
    except (TypeError, ValueError):
        return None
    return None


def _finite_spawn_point(x, y, z):
    point = {
        "x": float(x),
        "y": float(y),
        "z": float(z),
    }
    if not all(math.isfinite(component) for component in point.values()):
        return None
    return point


def _report_finalization_failure(
    upload_id,
    *,
    bucket,
    source_key,
    downloaded,
    processed_keys,
    error,
):
    try:
        _send_upload_status(
            upload_id,
            "failed",
            actual_size_bytes=downloaded.size_bytes,
            actual_sha256=downloaded.sha256,
            processing_error=f"Map finalization failed: {error}",
            metadata={
                "s3": {
                    "bucket": bucket,
                    "original_key": source_key,
                    "processed_original_key": processed_keys.get("original_map"),
                },
            },
        )
    except Exception as status_error:
        print(
            f"Failed to report map finalization failure for upload {upload_id}: "
            f"{status_error}"
        )


def _map_name_from_result(result_path, source_key):
    map_name = str(result_path.get("map_name") or Path(posixpath.basename(source_key)).stem).strip()
    if not map_name:
        raise NonRetryableMapError("Converted map result did not include a map name")
    return map_name


def _display_name_for_map(*, map_name, source_key, downloaded_metadata):
    raw_name = downloaded_metadata.get("original-filename") or posixpath.basename(source_key)
    display_name = Path(str(raw_name)).stem
    display_name = UUID_PATTERN.sub("", display_name).strip(" ._-")
    display_name = re.sub(r"[_-]+", " ", display_name)
    display_name = re.sub(r"\s+", " ", display_name).strip()
    if not display_name:
        display_name = map_name
    if display_name.islower():
        display_name = display_name.title()
    return display_name


def _upload_file(filename, bucket, key, content_type):
    print(f"Uploading {filename} to s3://{bucket}/{key}")
    _s3_client().upload_file(
        str(filename),
        bucket,
        key,
        ExtraArgs={"ContentType": content_type},
    )


def _copy_object(bucket, source_key, destination_key):
    if source_key == destination_key:
        return
    print(f"Copying s3://{bucket}/{source_key} to s3://{bucket}/{destination_key}")
    _s3_client().copy_object(
        Bucket=bucket,
        Key=destination_key,
        CopySource={"Bucket": bucket, "Key": source_key},
        MetadataDirective="COPY",
    )


def _delete_object(bucket, key):
    print(f"Deleting s3://{bucket}/{key}")
    _s3_client().delete_object(Bucket=bucket, Key=key)


def _processed_key(source_key, *, unprocessed_prefix, processed_prefix):
    if source_key.startswith(unprocessed_prefix):
        suffix = source_key[len(unprocessed_prefix) :]
    else:
        suffix = posixpath.basename(source_key)
    return f"{processed_prefix}{suffix.lstrip('/')}"


def _upload_id_from_key(key):
    match = UUID_PATTERN.search(key)
    if match is None:
        raise NonRetryableMapError("Map object key did not include an upload UUID")
    return match.group("upload_id").lower()


def _send_upload_status(
    upload_id,
    status,
    *,
    actual_size_bytes=None,
    actual_sha256=None,
    metadata=None,
    processing_error=None,
):
    payload = {
        "status": status,
        "metadata": {
            **(metadata or {}),
            "processor_runtime": {
                "name": PROCESSOR_NAME,
            },
        },
    }
    if actual_size_bytes is not None:
        payload["actual_size_bytes"] = actual_size_bytes
    if actual_sha256 is not None:
        payload["actual_sha256"] = actual_sha256
    if processing_error:
        payload["processing_error"] = str(processing_error)[:4096]

    _call_app_api(
        "PATCH",
        _settings()["processing_status_path_template"].format(upload_id=upload_id),
        payload,
    )


def _call_app_api(method, path, payload):
    settings = _settings()
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    timestamp = str(int(time.time()))
    base_url = settings["app_api_base_url"].rstrip("/")
    url = f"{base_url}{path}"
    parsed_url = urllib.parse.urlsplit(url)
    signature = _hmac_signature(
        client=settings["trusted_client_name"],
        timestamp=timestamp,
        method=method,
        raw_path=parsed_url.path,
        raw_query_string=parsed_url.query,
        body=body,
        secret=_secret_value(settings["trusted_client_secret_id"]),
    )
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Content-Type": "application/json",
            "X-Halospawns-Client": settings["trusted_client_name"],
            "X-Halospawns-Timestamp": timestamp,
            "X-Halospawns-Signature": f"sha256={signature}",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_body = response.read()
            return json.loads(response_body.decode("utf-8")) if response_body else {}
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise MapProcessingError(
            f"App API returned HTTP {error.code} for {method} {path}: {error_body[:1000]}"
        ) from error
    except urllib.error.URLError as error:
        raise MapProcessingError(f"App API request failed for {method} {path}: {error}") from error


def _hmac_signature(*, client, timestamp, method, raw_path, raw_query_string, body, secret):
    canonical_request = "\n".join(
        (
            "HALOSPAWNS-HMAC-SHA256",
            client,
            timestamp,
            method.upper(),
            raw_path,
            raw_query_string,
            hashlib.sha256(body).hexdigest(),
        )
    )
    return hmac.new(
        secret.encode("utf-8"),
        canonical_request.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _secret_value(secret_id):
    if secret_id not in SECRET_CACHE:
        response = _secrets_client().get_secret_value(SecretId=secret_id)
        secret = response.get("SecretString")
        if not secret:
            raise MapProcessingError(f"Trusted client secret was empty: {secret_id}")
        SECRET_CACHE[secret_id] = secret
    return SECRET_CACHE[secret_id]


def _settings():
    return {
        "app_api_base_url": _required_env("APP_API_BASE_URL"),
        "trusted_client_name": _required_env("APP_API_TRUSTED_CLIENT_NAME"),
        "trusted_client_secret_id": _required_env("APP_API_TRUSTED_CLIENT_HMAC_SECRET_ID"),
        "processing_status_path_template": os.getenv(
            "APP_API_UPLOAD_PROCESSING_STATUS_PATH_TEMPLATE",
            "/v1/uploads/{upload_id}/processing-status",
        ),
        "map_finalization_path": _path_env(
            "APP_API_MAP_FINALIZATION_PATH",
            "/v1/ingest/map-uploads",
        ),
        "unprocessed_prefix": _prefix_env("MAP_UNPROCESSED_PREFIX", "maps/unprocessed/"),
        "processed_prefix": _prefix_env("MAP_PROCESSED_PREFIX", "maps/processed/"),
        "failed_prefix": _prefix_env("MAP_FAILED_PREFIX", "maps/failed/"),
        "base_directory": os.environ.get("CE_PATH", "/tmp/ce"),
    }


def _required_env(name):
    value = os.getenv(name)
    if value is None or not value.strip():
        raise MapProcessingError(f"Missing required environment variable: {name}")
    return value.strip()


def _prefix_env(name, default):
    value = (os.getenv(name) or default).strip().strip("/")
    return f"{value}/"


def _path_env(name, default):
    value = (os.getenv(name) or default).strip()
    if not value.startswith("/"):
        value = f"/{value}"
    return value


def _bool_env(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes"}


def handler(event, context):
    event = _as_dict(event)
    results = []
    io_mode = resolve_io_mode(event)
    print(f"IO mode: {io_mode}")

    if io_mode == "local":
        results.extend(process_local_event(event))
        return {
            "statusCode": 200,
            "body": json.dumps(results, default=str),
        }

    failures = _process_s3_event(event, results)
    response = {
        "statusCode": 200,
        "body": json.dumps(results, default=str),
    }
    if _bool_env("REPORT_BATCH_ITEM_FAILURES", False):
        response["batchItemFailures"] = failures
    return response

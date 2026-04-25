import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import app


class HandlerIoModeTests(unittest.TestCase):
    def test_local_mode_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            map_path = tmp_path / "chillout.map"
            map_path.write_bytes(b"fake-map")
            base_dir = tmp_path / "ce"

            with patch("conversion_runtime.map_to_glb") as map_to_glb:
                map_to_glb.return_value = {
                    "glb": base_dir / "output" / "pat_chillout" / "pat_chillout.glb",
                    "blend": base_dir / "output" / "pat_chillout" / "pat_chillout.blend",
                    "meta": base_dir / "output" / "pat_chillout" / "pat_chillout.json",
                    "map_name": "pat_chillout",
                }
                event = {
                    "io_mode": "local",
                    "local_input_map": str(map_path),
                    "base_directory": str(base_dir),
                }
                response = app.handler(event, None)

            body = json.loads(response["body"])
            self.assertEqual(response["statusCode"], 200)
            self.assertEqual(body[0]["status"], "success")
            self.assertEqual(body[0]["input"], str(map_path.resolve()))
            map_to_glb.assert_called_once()

    def test_local_mode_missing_file_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            map_path = Path(tmpdir) / "missing.map"
            response = app.handler({"io_mode": "local", "local_input_map": str(map_path)}, None)
            body = json.loads(response["body"])

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body[0]["status"], "failure")
        self.assertIn("not found", body[0]["error"].lower())

    def test_s3_mode_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / "ce"
            s3_mock = MagicMock()

            with patch("app.boto3.client", return_value=s3_mock):
                with patch("conversion_runtime.map_to_glb") as map_to_glb:
                    map_to_glb.return_value = {
                        "glb": "/tmp/ce/output/pat_chillout/pat_chillout.glb",
                        "blend": "/tmp/ce/output/pat_chillout/pat_chillout.blend",
                        "meta": "/tmp/ce/output/pat_chillout/pat_chillout.json",
                        "map_name": "pat_chillout",
                    }
                    event = {
                        "base_directory": str(base_dir),
                        "Records": [
                            {
                                "messageId": "m1",
                                "body": json.dumps(
                                    {
                                        "MessageId": "sns1",
                                        "Message": json.dumps(
                                            {
                                                "Records": [
                                                    {
                                                        "eventName": "ObjectCreated:Put",
                                                        "s3": {
                                                            "bucket": {"name": "bucket-1"},
                                                            "object": {"key": "maps/unprocessed/chillout.map"},
                                                        },
                                                    }
                                                ]
                                            }
                                        ),
                                    }
                                ),
                            }
                        ],
                    }
                    response = app.handler(event, None)

            body = json.loads(response["body"])
            self.assertEqual(response["statusCode"], 200)
            self.assertEqual(body[0]["status"], "success")
            s3_mock.download_file.assert_called_once()
            self.assertEqual(s3_mock.upload_file.call_count, 2)


if __name__ == "__main__":
    unittest.main()

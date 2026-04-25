## Project Overview

This project is a map conversion service for Halo: Combat Evolved, designed to run as an AWS Lambda function within a Docker container. It converts `.map` files into `.glb` and `.blend` formats, extracting geometry, textures, lightmaps, and gameplay metadata (spawns, equipment, etc.).

## Tooling & Dependencies

*   **Refinery (MEK)**: Used for `.map` tag extraction.
*   **AetherCLI**: Used for converting Halo tags to OBJ format.
*   **Blender 2.93**: Used for UV merging, material setup, and GLB export.
*   **AWS Lambda / Docker**: The runtime environment. The Dockerfile sets up a Python 3.14 environment with .NET (for AetherCLI) and Blender 2.93 pre-installed.

## Execution Flow Trace

The execution follows this path from start to finish:

1.  **Trigger**: S3 event (.map file uploaded) -> SNS -> SQS -> Lambda.
2.  **Entrypoint (`app.handler`)**:
    *   The Lambda runtime calls the `handler` function in `app.py`.
    *   It parses the SQS/SNS/S3 event to identify the source bucket and key.
    *   The `.map` file is downloaded from S3 to `/tmp/ce/input/`.
    *   The conversion process is initiated by calling `map_to_glb` in `convert_map.py`.
3.  **Map Conversion (`convert_map.py`)**:
    *   **Tag Extraction (`map_to_scenario.py`)**: Uses the **Refinery** tool (from the MEK project) to extract the `.scenario` tag and all associated data from the `.map` file into `/tmp/ce/tags/` and `/tmp/ce/data/`.
    *   **Metadata Extraction**: While extracting tags, it also gathers gameplay metadata (player spawns, equipment locations, teleporters) and shader attributes (radiosity power, textures) into a `.json` metadata file. Lightmap PNGs are base64-encoded into this JSON for later processing.
    *   **OBJ Generation (`scenario_to_obj.py`)**: Calls **AetherCLI** (a .NET tool) to convert the extracted `.scenario` file into OBJ format (one for the BSP geometry and one for lightmap geometry).
    *   **OBJ Post-processing (`obj_cleanup.py`)**: 
        *   Cleans up OBJ/MTL files (removes quotes/spaces from paths).
        *   Combines multiple lightmap PNGs into a single `lightmap.png`.
        *   Updates the lightmap OBJ's UV coordinates to match the newly combined atlas.
    *   **Blender Processing (`blender_293.py`)**: 
        *   Launches Blender 2.93 in background mode.
        *   Imports the BSP and lightmap OBJs.
        *   Transfers the lightmap UVs as a second UV channel onto the main BSP object.
        *   Applies material properties (alpha testing, shader types) from the metadata JSON.
        *   Exports the final scene to `.glb` and saves a `.blend` file.
4.  **Finalization (`app.handler`)**:
    *   The resulting `.glb` and `.blend` files are uploaded back to the S3 bucket under `maps/processed/`.
    *   The Lambda function returns a success status with the S3 paths of the generated assets.

## Local Testing

### Handler IO modes

`app.py` supports two handler modes:

- `IO_MODE=s3` (default): current SNS/SQS/S3 flow
- `IO_MODE=local`: run conversion from a local file path and skip S3 download/upload

`IO_MODE=local` inputs can come from event JSON or environment variables:

- `local_input_map` / `LOCAL_INPUT_MAP`
- `base_directory` / `CE_PATH`
- `output_directory` / `OUTPUT_DIRECTORY`
- `input_directory` / `INPUT_DIRECTORY`
- `stage_local_input` / `STAGE_LOCAL_INPUT`

### Local Python E2E

```powershell
python .\tests\e2e\run_local_e2e.py `
  --map-path "$HOME\maps\chillout.map" `
  --base-directory "$HOME\ce" `
  --output-directory "$HOME\ce\output" `
  --expected-min-images 300 `
  --max-duration-ms 30000
```

### Local container E2E (RIE + mounted folders, no S3)

```powershell
.\tests\e2e\run_container_local_e2e.ps1 `
  -MapPath "$HOME\maps\chillout.map" `
  -CeRoot "$HOME\ce_container_test"
```

### Output validation only

```powershell
python .\tests\validation\validate_conversion_run.py `
  --output-map-dir "$HOME\ce\output\pat_chillout" `
  --map-name "pat_chillout" `
  --log-file ".\test_local_convert_map_console_output.log" `
  --baseline-output-listing ".\tests\baselines\output_folder_contents.txt" `
  --expected-min-images 300 `
  --max-duration-ms 30000
```

### Example commands run during implementation

```powershell
# from repo root
Set-Location "$HOME\projects\halospawns-tools"

# handler IO mode unit tests
python -m unittest tests.test_app_io_modes

# validate against local conversion log
python .\tests\validation\validate_conversion_run.py `
  --output-map-dir "$HOME\ce\output\pat_chillout" `
  --map-name "pat_chillout" `
  --log-file ".\test_local_convert_map_console_output.log" `
  --baseline-output-listing ".\tests\baselines\output_folder_contents.txt" `
  --expected-min-images 300 `
  --max-duration-ms 30000

# validate against container conversion log
python .\tests\validation\validate_conversion_run.py `
  --output-map-dir "$HOME\ce\output\pat_chillout" `
  --map-name "pat_chillout" `
  --log-file ".\test_event_container_console_output.log" `
  --baseline-output-listing ".\tests\baselines\output_folder_contents.txt" `
  --expected-min-images 300 `
  --max-duration-ms 30000

# full local E2E run + validation
python .\tests\e2e\run_local_e2e.py `
  --map-path "$HOME\maps\chillout.map" `
  --base-directory "$HOME\ce" `
  --output-directory "$HOME\ce\output" `
  --baseline-output-listing ".\tests\baselines\output_folder_contents.txt" `
  --expected-min-images 300 `
  --max-duration-ms 30000
```

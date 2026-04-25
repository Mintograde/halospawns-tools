$imageName = "halospawns-tools"
$imageTag = "latest"
$aetherTag = "v1.0.8"
$environment = "dev"

$env:DOCKER_BUILDKIT = 1
$dockerCommand = "docker build --progress=plain --provenance=false --platform linux/amd64 --build-arg AETHER_TAG=$aetherTag -t $($imageName):$imageTag ."
Write-Host "Running Docker build command:"
Write-Host $dockerCommand

Invoke-Expression $dockerCommand

Write-Host "Build complete. Image '$($imageName):$imageTag' created."

$imageUri = "283279960672.dkr.ecr.us-east-1.amazonaws.com/$($imageName):$imageTag"

aws ecr get-login-password --region us-east-1 --profile "halospawns-$environment" | docker login --username AWS --password-stdin "283279960672.dkr.ecr.us-east-1.amazonaws.com"
docker tag "$($imageName):$imageTag" $imageUri
docker push $imageUri

aws lambda update-function-code --profile "halospawns-$environment" --function-name "halospawns-tools-$environment" --image-uri $imageUri

# NOTE: to test locally via RIE (S3 mode), you can do this:
#$dirPath = "$HOME\.aws-lambda-rie"
#if (-not (Test-Path $dirPath)) { New-Item -Path $dirPath -ItemType Directory | Out-Null }
#Invoke-WebRequest -Uri "https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie" -OutFile "$dirPath\aws-lambda-rie"
#docker run --platform linux/amd64 -p 9000:8080 `
#  -v "$HOME\.aws-lambda-rie:/aws-lambda" `
#  -v "$HOME\.aws:/root/.aws:ro" `
#  -e AWS_PROFILE=halospawns-$environment `
#  --entrypoint /aws-lambda/aws-lambda-rie `
#  halospawns-tools:latest `
#  /usr/local/bin/python -m awslambdaric app.handler
#curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d "@testevent.json"

# NOTE: to test locally via mounted folders (no S3), use IO_MODE=local:
#$localMapFolder = "L:\path\to\maps"
#$localCeRoot = "L:\ce_container_test"
#docker run --platform linux/amd64 -p 9000:8080 `
#  -v "$HOME\.aws-lambda-rie:/aws-lambda" `
#  -v "${localMapFolder}:/local_input:ro" `
#  -v "${localCeRoot}:/tmp/ce" `
#  -e IO_MODE=local `
#  --entrypoint /aws-lambda/aws-lambda-rie `
#  halospawns-tools:latest `
#  /usr/local/bin/python -m awslambdaric app.handler
#curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d "@tests/events/testevent_local.json"

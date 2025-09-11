$imageName = "halospawns-tools"
$imageTag = "latest"
$aetherTag = "v1.0.8"
$environment = "dev"

$env:DOCKER_BUILDKIT = 1
$dockerCommand = "docker build --progress=plain --build-arg AETHER_TAG=$aetherTag -t $($imageName):$imageTag ."
Write-Host "Running Docker build command:"
Write-Host $dockerCommand

Invoke-Expression $dockerCommand

Write-Host "Build complete. Image '$($imageName):$imageTag' created."

$imageUri = "283279960672.dkr.ecr.us-east-1.amazonaws.com/$($imageName):$imageTag"

aws ecr get-login-password --region us-east-1 --profile "halospawns-$environment" | docker login --username AWS --password-stdin "283279960672.dkr.ecr.us-east-1.amazonaws.com"
docker tag "$($imageName):$imageTag" $imageUri
docker push $imageUri

aws lambda update-function-code --profile "halospawns-$environment" --function-name "halospawns-tools-$environment" --image-uri $imageUri

# NOTE: to test locally, you can do this:
# docker run -p 9000:8080 -v "$HOME/.aws:/root/.aws:ro" -e AWS_PROFILE=halospawns-$environment halospawns-tools:latest
# curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d "@testevent.json"
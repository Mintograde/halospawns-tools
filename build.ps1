$imageName = "halospawns-tools"
$imageTag = "latest"
$patPath = "$HOME/.github/github_pat"
$aetherTag = "v1.0.8"
$environment = "dev"

if (-not (Test-Path $patPath)) {
    Write-Error "GitHub PAT not found at '$patPath'. Please create the file and paste your token in it."
    exit 1
}

$env:DOCKER_BUILDKIT = 1
$dockerCommand = "docker build --secret id=github_pat,src=$patPath --progress=plain --build-arg AETHER_TAG=$aetherTag -t $($imageName):$imageTag ."
Write-Host "Running Docker build command:"
Write-Host $dockerCommand

Invoke-Expression $dockerCommand

Remove-Item Env:\DOCKER_BUILDKIT
Write-Host "Build complete. Image '$($imageName):$imageTag' created."

$imageUri = "283279960672.dkr.ecr.us-east-1.amazonaws.com/$($imageName):$imageTag"

aws ecr get-login-password --region us-east-1 --profile halospawns-dev | docker login --username AWS --password-stdin "283279960672.dkr.ecr.us-east-1.amazonaws.com"
docker tag "$($imageName):$imageTag" $imageUri
docker push $imageUri

aws lambda update-function-code --profile "halospawns-$environment" --function-name "halospawns-tools-$environment" --image-uri $imageUri

# NOTE: to test locally, you can do this:
# docker run -p 9000:8080 -v C:/users/minto/.aws:/root/.aws:ro -e AWS_PROFILE=halospawns-dev halospawns-tools:latest
# curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d "@testevent.json"
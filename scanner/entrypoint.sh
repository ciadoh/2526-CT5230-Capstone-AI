#!/bin/bash
set -e

REPO="${TARGET_REPO:-expressjs/express}"
REPO_NAME=$(echo "$REPO" | cut -d'/' -f2)
PROJECT_KEY=$(echo "$REPO" | tr '/' '-')

echo "==> Cloning ${REPO}..."
if [ ! -d "/workspace/${REPO_NAME}" ]; then
  if [ -n "$GITHUB_TOKEN" ]; then
    git -c http.sslVerify=false clone --depth=50 "https://${GITHUB_TOKEN}@github.com/${REPO}.git" "/workspace/${REPO_NAME}"
  else
    git -c http.sslVerify=false clone --depth=50 "https://github.com/${REPO}.git" "/workspace/${REPO_NAME}"
  fi
fi

echo "==> Waiting for SonarQube..."
until curl -sfk "${SONAR_HOST_URL}/api/system/status" | grep -q '"status":"UP"'; do
  sleep 5
done

echo "==> Creating SonarQube project..."
curl -sfk -u "${SONAR_TOKEN}:" -X POST \
  "${SONAR_HOST_URL}/api/projects/create" \
  -d "name=${REPO_NAME}&project=${PROJECT_KEY}" || true

cd "/workspace/${REPO_NAME}"

if [ -f "pom.xml" ]; then
  echo "==> Detected Maven project — building and scanning with mvn sonar:sonar..."
  MVN_SSL="-Dmaven.wagon.http.ssl.insecure=true -Dmaven.wagon.http.ssl.allowall=true -Dmaven.wagon.http.ssl.ignore.validity.dates=true"

  echo "==> Compiling Java project..."
  mvn -B --no-transfer-progress -Dmaven.test.skip=true $MVN_SSL compile || true

  echo "==> Running sonar:sonar..."
  mvn -B --no-transfer-progress -Dmaven.test.skip=true $MVN_SSL \
    sonar:sonar \
    -Dsonar.projectKey="${PROJECT_KEY}" \
    -Dsonar.projectName="${REPO_NAME}" \
    -Dsonar.host.url="${SONAR_HOST_URL}" \
    -Dsonar.token="${SONAR_TOKEN}" \
    -Dsonar.scanner.skipSystemTruststore=true \
    -Dsonar.exclusions="**/node_modules/**,**/dist/**,**/*.test.*,**/coverage/**"
else
  echo "==> Running sonar-scanner (JS/TS/other)..."
  sonar-scanner \
    -Dsonar.projectKey="${PROJECT_KEY}" \
    -Dsonar.projectName="${REPO_NAME}" \
    -Dsonar.sources=. \
    -Dsonar.host.url="${SONAR_HOST_URL}" \
    -Dsonar.token="${SONAR_TOKEN}" \
    -Dsonar.javascript.lcov.reportPaths=coverage/lcov.info \
    -Dsonar.exclusions="**/node_modules/**,**/dist/**,**/*.test.*,**/coverage/**" \
    -Dsonar.scanner.truststorePath="" \
    -Dsonar.scanner.skipSystemTruststore=true
fi

echo "==> Scan complete."

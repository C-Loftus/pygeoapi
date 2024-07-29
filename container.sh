mkdir .devcontainer

touch .devcontainer/devcontainer.json

echo '{"name":"my-container","version":"1.0","settings":{"theme":"dark","editor":"vscode"},"extensions":["ms-python.python","ms-vscode.cpptools"]}' > .devcontainer/devcontainer.json

cat <<EOF > docker-compose.yml
version: '3'

services:
  pygeoapi:
    build: .
    container_name: pygeoapi
    ports:
      - "5000:80"
    volumes:
      - ./pygeoapi:/pygeoapi/pygeoapi  # Map the pygeoapi directory into /code/pygeoapi in the container
      - ./tests:/pygeoapi/tests         # Map the test directory into /code/test in the container
EOF

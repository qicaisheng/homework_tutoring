# !/bin/bash

PARENT_DIR=$(dirname $(pwd))

docker run --name homework_turoring_nginx_container \
    -v ${PARENT_DIR}/data:/usr/share/nginx/html:ro \
    -v $(pwd)/nginx.conf:/etc/nginx/nginx.conf:ro \
    -p 18080:80 -d nginx

#!/bin/sh

run:
	docker compose -f ./01-docker-compose/docker-compose_flask_minio.yml up
	docker tag 01-docker-compose_app userdata:1.0.1

rm:
	docker rm -f userdata-app userdata-minio

rmi:
	docker rmi 01-docker-compose_app minio/minio minio/mc userdata

clean:
	docker rm -f userdata-app userdata-mc userdata-minio
	docker rmi 01-docker-compose_app minio/minio minio/mc userdata


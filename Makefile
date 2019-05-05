APP_NAME=py-orbi-smartthings-presence

.PHONY : all stop remove build up start run check-cache bash

all : build up run check-cache

stop :
	docker container stop $(APP_NAME) || true

remove : stop
	docker container rm $(APP_NAME) || true

build : remove
	docker build -t $(APP_NAME) .

up :
	docker run  -d --name $(APP_NAME) $(APP_NAME)

start :
	docker start $(APP_NAME)

run : start
	docker exec $(APP_NAME) python scan-devices.py

check-cache : start
	docker exec $(APP_NAME) cat cache.yml

bash : start
	docker exec $(APP_NAME) bash

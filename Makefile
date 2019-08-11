APP_NAME=py-orbi-smartthings-presence
DB_LOCATION=/usr/src/app/device_history

.PHONY : all stop remove build up start run check-cache bash

all : build up run check-cache check-devices stop

stop :
	docker container stop $(APP_NAME) || true

remove : stop
	docker container rm $(APP_NAME) || true

build : remove
	docker build -t $(APP_NAME) .

up :
	docker run -i -d --name $(APP_NAME) -v ~/orbi_device_history:$(DB_LOCATION) $(APP_NAME)

start :
	docker start $(APP_NAME)

run : start
	docker exec $(APP_NAME) python scan-devices.py

rm-db :
	sudo rm -f $(DB_LOCATION)/pyOrbiSmartthings.db

check-cache : start
	docker exec -it $(APP_NAME) sqlite3 $(DB_LOCATION)/pyOrbiSmartthings.db "SELECT * FROM cache;"

check-devices : start
	docker exec -it $(APP_NAME) sqlite3 $(DB_LOCATION)/pyOrbiSmartthings.db "SELECT * FROM devices;"

bash : start
	docker exec -it $(APP_NAME) bash

sql : start
	docker exec -it $(APP_NAME) sqlite3 $(DB_LOCATION)/pyOrbiSmartthings.db

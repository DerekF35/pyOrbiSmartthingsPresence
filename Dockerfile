FROM python:3

RUN apt-get update \
	&& apt-get install -y sqlite3 libsqlite3-dev \
	&& rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

ENV TZ=America/New_York
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY config.yml scan-devices.py ./

RUN mkdir -p device_history

CMD [ "bash" ]

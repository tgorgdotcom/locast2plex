FROM jrottenberg/ffmpeg:4.0-alpine
LABEL maintainer="Thomas Gorgolione <thomas@tgorg.com>"

RUN apk add --no-cache --update python
COPY main.py /app/main.py
COPY fcc_dma_markets.json /app/fcc_dma_markets.json
COPY known_stations.json /app/known_stations.json
COPY templates.py /app/templates.py
COPY SSDPServer.py /app/SSDPServer.py
COPY LocastService.py /app/LocastService.py
COPY tv_stations.json /app/tv_stations.json
COPY m3u8/ /app/m3u8/
RUN (cat /dev/urandom | tr -dc 'h-z' | fold -w 8 | head -n 1) > /app/service_uuid

ENV username='username' password='password' external_addy='0.0.0.0' external_port='6077' debug='false'
ENTRYPOINT ["python", "/app/main.py", "2>&1"]
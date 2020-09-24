FROM jrottenberg/ffmpeg:4.0-alpine
LABEL maintainer="Thomas Gorgolione <thomas@tgorg.com>"

RUN apk add --no-cache --update python3
COPY main.py /app/main.py
COPY fcc_dma_markets.json /app/fcc_dma_markets.json
COPY known_stations.json /app/known_stations.json
COPY templates.py /app/templates.py
COPY SSDPServer.py /app/SSDPServer.py
COPY LocastService.py /app/LocastService.py
COPY tv_stations.json /app/tv_stations.json
COPY m3u8/ /app/m3u8/

ENTRYPOINT ["python3", "/app/main.py", "2>&1"]

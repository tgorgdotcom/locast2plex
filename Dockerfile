FROM jrottenberg/ffmpeg:4.0-alpine
LABEL maintainer="Thomas Gorgolione <thomas@tgorg.com>"

RUN apk add --no-cache --update python3
COPY data /app/data
COPY *.py /app/
COPY m3u8/ /app/m3u8/

ENTRYPOINT ["python3", "/app/main.py", "2>&1"]

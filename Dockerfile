FROM jrottenberg/ffmpeg:4.0-alpine
LABEL maintainer="Thomas Gorgolione <thomas@tgorg.com>"

RUN apk  add --no-cache --update python
COPY main.py /app/main.py
COPY telly.config.toml /etc/telly/telly.config.toml
COPY m3u8/ /app/m3u8/
COPY --from=tellytv/telly:dev /app /app/telly

EXPOSE 6077
ENV username='username' password='password' listen_addy='0.0.0.0'
ENTRYPOINT ["python", "/app/main.py"]
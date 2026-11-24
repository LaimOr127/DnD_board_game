FROM python:3.13-slim-bookworm@sha256:1cbf5090b131eace73aff87e4e5d3d27900ee5ffbe8d61fa2ede4bd6e231c7cf

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY site/ site/
COPY build/ build/
COPY design/ design/
COPY ["Море имён/", "Море имён/"]
COPY ["Кубики/", "Кубики/"]
RUN mkdir /data && chown 10001:10001 /data
USER 10001:10001
EXPOSE 8765
CMD ["python", "site/server.py", "--bind", "0.0.0.0", "--db", "/data/rooms.sqlite3"]

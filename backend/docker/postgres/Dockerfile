# Official Postgres 17 + PostGIS from Debian packages: postgis/postgis publishes no ARM (Apple Silicon) image.
FROM postgres:17
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-17-postgis-3 \
    && rm -rf /var/lib/apt/lists/*

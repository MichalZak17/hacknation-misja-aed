"""PostGIS without GeoDjango: a generated `geom geography(Point)` column from lat/lon with a GiST index (nearest-AED,
bounding-box and duplicate-candidate queries are index lookups), and the sequence behind AED-PL-{n} device IDs."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("devices", "0001_initial")]

    operations = [
        migrations.RunSQL(
            sql=[
                "CREATE EXTENSION IF NOT EXISTS postgis",
                "CREATE SEQUENCE IF NOT EXISTS device_id_seq START 1",
                """
                ALTER TABLE devices_device ADD COLUMN geom geography(Point, 4326)
                GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography) STORED
                """,
                "CREATE INDEX devices_device_geom_gist ON devices_device USING GIST (geom)",
                "CREATE INDEX devices_device_sources_gin ON devices_device USING GIN (sources jsonb_path_ops)",
            ],
            reverse_sql=[
                "DROP INDEX IF EXISTS devices_device_sources_gin",
                "DROP INDEX IF EXISTS devices_device_geom_gist",
                "ALTER TABLE devices_device DROP COLUMN IF EXISTS geom",
                "DROP SEQUENCE IF EXISTS device_id_seq",
            ],
        )
    ]

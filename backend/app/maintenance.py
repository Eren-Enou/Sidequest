"""Explicit Sidequest transfer, logical backup and empty-database recovery tools."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess

from sqlalchemy import create_engine, event, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from app.database import BACKEND_ROOT, WRITE_LOCK_NAMESPACE, WRITE_LOCK_KEY
from app.migrate import require_current_schema
from app.models import Game, Goal, PlaySession
from app.schemas import GameRead, GoalRead
from app.session_schemas import SessionRead

TABLES = ((Game, GameRead), (Goal, GoalRead), (PlaySession, SessionRead))


class MaintenanceError(RuntimeError):
    pass


def postgres_url(value):
    try:
        url = make_url(value)
        if url.drivername not in {"postgresql", "postgresql+psycopg"} or not url.host or not url.database:
            raise ValueError()
        return url.set(drivername="postgresql+psycopg")
    except Exception:
        raise MaintenanceError("Maintenance requires an explicit PostgreSQL Psycopg URL") from None


def destination_engine(value):
    try:
        return create_engine(postgres_url(value), poolclass=NullPool, hide_parameters=True,
                             isolation_level="READ COMMITTED")
    except MaintenanceError:
        raise
    except Exception:
        raise MaintenanceError("Cannot initialize maintenance database") from None


def readonly_sqlite(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise MaintenanceError("SQLite source must be an existing file")
    engine = create_engine("sqlite+pysqlite://", creator=lambda: sqlite3.connect(
        path.as_uri() + "?mode=ro", uri=True, isolation_level=None), hide_parameters=True)

    @event.listens_for(engine, "connect")
    def configure(connection, _):
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA foreign_keys=ON")

    @event.listens_for(engine, "begin")
    def begin(connection):
        connection.exec_driver_sql("BEGIN")
    return engine


def lock(connection):
    connection.execute(text("SELECT pg_advisory_xact_lock(:namespace, :key)"),
                       {"namespace": WRITE_LOCK_NAMESPACE, "key": WRITE_LOCK_KEY})


def records(connection):
    return {model.__tablename__: [dict(row) for row in connection.execute(
        select(model.__table__).order_by(model.id)).mappings()] for model, _ in TABLES}


def digest(data):
    # Hash logical values without projecting/replacing the original snapshots.
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False,
                         default=lambda value: value.astimezone(timezone.utc).isoformat()).encode()
    return hashlib.sha256(encoded).hexdigest()


def transfer(source, destination, dry_run=False):
    if source.dialect.name != "sqlite" or destination.dialect.name != "postgresql":
        raise MaintenanceError("Transfer requires SQLite source and PostgreSQL destination")
    try:
        require_current_schema(source)
        require_current_schema(destination)
        with source.connect() as origin, origin.begin(), destination.connect() as target:
            transaction = target.begin()
            try:
                lock(target)
                require_current_schema(destination)
                tables = set(inspect(target).get_table_names())
                if tables != {"games", "goals", "play_sessions", "schema_migrations"}:
                    raise MaintenanceError("Destination must contain only the migrated Sidequest schema")
                if any(target.execute(select(model.id).limit(1)).first() for model, _ in TABLES):
                    raise MaintenanceError("Destination domain tables must be empty; overwrite is unsupported")
                if origin.exec_driver_sql("PRAGMA foreign_key_check").first():
                    raise MaintenanceError("Source relationships are invalid")
                data = records(origin)
                for model, schema in TABLES:
                    for row in data[model.__tablename__]:
                        schema.model_validate(row)  # validate only; never serialize this projection
                    if data[model.__tablename__]:
                        target.execute(model.__table__.insert(), data[model.__tablename__])
                if records(target) != data:
                    raise MaintenanceError("Transferred data does not match source")
                for model, _ in TABLES:
                    largest = max((row["id"] for row in data[model.__tablename__]), default=0)
                    if largest >= 2 ** 63 - 1:
                        raise MaintenanceError("Transferred IDs leave no supported next ID")
                    sequence = target.execute(text("SELECT pg_get_serial_sequence(:table, 'id')"),
                                              {"table": model.__tablename__}).scalar_one()
                    preparer = target.dialect.identifier_preparer
                    quoted = ".".join(preparer.quote(part) for part in preparer.unformat_identifiers(sequence))
                    # ALTER SEQUENCE is transactional; setval would leak through a dry-run rollback.
                    target.exec_driver_sql(f"ALTER SEQUENCE {quoted} RESTART WITH {max(1, largest + 1)}")
                summary = {"counts": {name: len(rows) for name, rows in data.items()},
                           "sha256": digest(data), "dry_run": dry_run}
                transaction.rollback() if dry_run else transaction.commit()
                return summary
            finally:
                if transaction.is_active:
                    transaction.rollback()
    except MaintenanceError:
        raise
    except Exception:
        raise MaintenanceError("Transfer failed; destination transaction rolled back; check schema and source privately") from None


PG_QUERY_ENV = {"sslmode": "PGSSLMODE", "sslrootcert": "PGSSLROOTCERT", "sslcert": "PGSSLCERT",
                "sslkey": "PGSSLKEY", "sslcrl": "PGSSLCRL",
                "channel_binding": "PGCHANNELBINDING", "connect_timeout": "PGCONNECT_TIMEOUT",
                "options": "PGOPTIONS", "application_name": "PGAPPNAME",
                "target_session_attrs": "PGTARGETSESSIONATTRS", "gssencmode": "PGGSSENCMODE"}


def client_environment(value):
    url = postgres_url(value)
    if set(url.query) - set(PG_QUERY_ENV) or any(not isinstance(val, str) for val in url.query.values()):
        raise MaintenanceError("Unsupported maintenance connection option; refuse dropping it")
    env = {key: val for key, val in os.environ.items() if not key.startswith("PG")}
    env.update(PGHOST=url.host, PGPORT=str(url.port or 5432), PGDATABASE=url.database,
               PGUSER=url.username or "", PGAPPNAME="sidequest-maintenance")
    if url.password is not None:
        env["PGPASSWORD"] = url.password
    env.update({PG_QUERY_ENV[key]: val for key, val in url.query.items()})
    return env


def tool(name, directory=None):
    executable = Path(directory) / (name + (".exe" if os.name == "nt" else "")) if directory else shutil.which(name)
    if not executable or not Path(executable).is_file():
        raise MaintenanceError("PostgreSQL client tools are unavailable; set --pg-bin or PATH")
    return str(executable)


def run(command, env):
    try:
        result = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode:
            raise MaintenanceError("PostgreSQL client command failed; inspect configuration privately")
        return result.stdout
    except MaintenanceError:
        raise
    except Exception:
        raise MaintenanceError("Cannot execute PostgreSQL client command") from None


def backup(value, directory, pg_bin=None):
    env = client_environment(value)
    directory = Path(directory).resolve()
    if not directory.is_dir() or directory.is_relative_to(BACKEND_ROOT.parent):
        raise MaintenanceError("Backup directory must already exist outside the repository/provider")
    engine = destination_engine(value)
    try:
        require_current_schema(engine)
    except Exception:
        raise MaintenanceError("Backup requires a current Sidequest database; check maintenance configuration privately") from None
    finally:
        engine.dispose()
    timestamp = datetime.now(timezone.utc)
    path = directory / timestamp.strftime("sidequest-%Y-%m-%dT%H%M%SZ.dump")
    try:
        with path.open("xb"):
            pass
    except FileExistsError:
        raise MaintenanceError("Backup filename already exists; previous backup is preserved") from None
    except OSError:
        raise MaintenanceError("Cannot reserve backup output") from None
    try:
        run([tool("pg_dump", pg_bin), "--format=custom", "--no-owner", "--no-acl",
             "--file", str(path), "--dbname", ""], env)
        if not run([tool("pg_restore", pg_bin), "--list", str(path)], env):
            raise MaintenanceError("Backup archive is empty")
        return {"file": path.name, "timestamp": timestamp.isoformat(), "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    except Exception:
        path.unlink(missing_ok=True)
        raise


def restore(value, archive, pg_bin=None):
    path = Path(archive).resolve()
    if not path.is_file():
        raise MaintenanceError("Restore archive must be an existing trusted custom-format dump")
    env = client_environment(value)
    engine = destination_engine(value)
    try:
        with engine.begin() as connection:
            lock(connection)
            user_objects = connection.execute(text("""SELECT 1 FROM pg_class c
                JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname != 'information_schema'
                AND c.relkind IN ('r','p','f','S','v','m') LIMIT 1""")).first()
            if user_objects:
                raise MaintenanceError("Restore requires an empty database; destructive replacement is unsupported")
            run([tool("pg_restore", pg_bin), "--single-transaction", "--exit-on-error",
                 "--no-owner", "--no-acl", "--dbname", "", str(path)], env)
        require_current_schema(engine)
        with engine.connect() as connection:
            data = records(connection)
            for model, schema in TABLES:
                for row in data[model.__tablename__]:
                    schema.model_validate(row)
            return {"counts": {name: len(rows) for name, rows in data.items()}, "sha256": digest(data)}
    except MaintenanceError:
        raise
    except Exception:
        raise MaintenanceError("Restore or post-restore validation failed; keep target isolated and investigate privately") from None
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    copying = commands.add_parser("transfer")
    copying.add_argument("--source", required=True, help="Existing SQLite file; opened read-only")
    copying.add_argument("--dry-run", action="store_true")
    dumping = commands.add_parser("backup")
    dumping.add_argument("--directory", required=True)
    recovering = commands.add_parser("restore")
    recovering.add_argument("--archive", required=True)
    for command in (dumping, recovering):
        command.add_argument("--pg-bin", help="Directory containing compatible PostgreSQL client tools")
    args = parser.parse_args()
    try:
        value = os.environ.get("SIDEQUEST_MAINTENANCE_DATABASE_URL")
        postgres_url(value)
        if args.operation == "transfer":
            source, destination = readonly_sqlite(args.source), destination_engine(value)
            try:
                result = transfer(source, destination, args.dry_run)
            finally:
                source.dispose()
                destination.dispose()
        elif args.operation == "backup":
            result = backup(value, args.directory, args.pg_bin)
        else:
            result = restore(value, args.archive, args.pg_bin)
        print(json.dumps(result))
    except MaintenanceError as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()

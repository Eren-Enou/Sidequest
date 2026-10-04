"""ORM mappings; dialect-specific migration streams are authoritative schema DDL."""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, ForeignKeyConstraint, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator


def utcnow():
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """SQLite stores naive UTC; PostgreSQL stores TIMESTAMPTZ; domain values are UTC."""
    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(DateTime(timezone=dialect.name == "postgresql"))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timestamp must be timezone aware")
        value = value.astimezone(timezone.utc)
        return value if dialect.name == "postgresql" else value.replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.astimezone(timezone.utc) if dialect.name == "postgresql" else value.replace(tzinfo=timezone.utc)


class Base(DeclarativeBase):
    pass


ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class Game(Base):
    __tablename__ = "games"
    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    current_interest: Mapped[int] = mapped_column(default=3)
    friction: Mapped[int] = mapped_column(default=0)
    energy_required: Mapped[str] = mapped_column(String(6))
    social_mode: Mapped[str] = mapped_column(String(6))
    experience_tags: Mapped[list[str]] = mapped_column(JSON)
    archived_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    goals: Mapped[list["Goal"]] = relationship(back_populates="game", passive_deletes="all")


class Goal(Base):
    __tablename__ = "goals"
    __table_args__ = (UniqueConstraint("id", "game_id"),)
    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True)
    game_id: Mapped[int] = mapped_column(ID_TYPE, ForeignKey("games.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    estimated_minutes: Mapped[int] = mapped_column(ID_TYPE)
    priority: Mapped[int] = mapped_column(default=2)
    status: Mapped[str] = mapped_column(String(9), default="active")
    readiness: Mapped[str] = mapped_column(String(7), default="current", server_default="current")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    game: Mapped[Game] = relationship(back_populates="goals")
    play_sessions: Mapped[list["PlaySession"]] = relationship(back_populates="goal", passive_deletes="all")


class PlaySession(Base):
    __tablename__ = "play_sessions"
    __table_args__ = (ForeignKeyConstraint(["goal_id", "game_id"], ["goals.id", "goals.game_id"], ondelete="RESTRICT"),)
    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True)
    game_id: Mapped[int] = mapped_column(ID_TYPE, ForeignKey("games.id", ondelete="RESTRICT"))
    goal_id: Mapped[int] = mapped_column(ID_TYPE)
    game_title_snapshot: Mapped[str] = mapped_column(String(200))
    goal_title_snapshot: Mapped[str] = mapped_column(String(200))
    started_at: Mapped[datetime] = mapped_column(UTCDateTime)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    actual_duration_minutes: Mapped[int | None] = mapped_column(ID_TYPE)
    enjoyment_rating: Mapped[int | None] = mapped_column(Integer)
    progress: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    situation_snapshot: Mapped[dict] = mapped_column(JSON)
    recommendation_snapshot: Mapped[dict] = mapped_column(JSON)
    goal: Mapped[Goal] = relationship(back_populates="play_sessions")

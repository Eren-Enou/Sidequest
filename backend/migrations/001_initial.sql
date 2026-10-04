CREATE TABLE games (
    id INTEGER PRIMARY KEY,
    title VARCHAR(200) NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 200),
    notes TEXT,
    current_interest INTEGER NOT NULL DEFAULT 3 CHECK (typeof(current_interest) = 'integer' AND current_interest BETWEEN 1 AND 5),
    friction INTEGER NOT NULL DEFAULT 0 CHECK (typeof(friction) = 'integer' AND friction BETWEEN 0 AND 5),
    energy_required VARCHAR(6) NOT NULL CHECK (energy_required IN ('low','medium','high')),
    social_mode VARCHAR(6) NOT NULL CHECK (social_mode IN ('solo','social','both')),
    experience_tags JSON NOT NULL CHECK (
        json_valid(experience_tags) AND json_type(experience_tags) = 'array'
        AND json_array_length(experience_tags) BETWEEN 1 AND 4
        AND json_type(experience_tags,'$[0]') = 'text'
        AND json_extract(experience_tags,'$[0]') IN ('progression','chill','challenge','novelty')
        AND (json_array_length(experience_tags) < 2 OR (json_type(experience_tags,'$[1]') = 'text' AND json_extract(experience_tags,'$[1]') IN ('progression','chill','challenge','novelty')))
        AND (json_array_length(experience_tags) < 3 OR (json_type(experience_tags,'$[2]') = 'text' AND json_extract(experience_tags,'$[2]') IN ('progression','chill','challenge','novelty')))
        AND (json_array_length(experience_tags) < 4 OR (json_type(experience_tags,'$[3]') = 'text' AND json_extract(experience_tags,'$[3]') IN ('progression','chill','challenge','novelty')))
    ),
    archived_at DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL CHECK (updated_at >= created_at)
);

CREATE TABLE goals (
    id INTEGER PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE RESTRICT,
    title VARCHAR(200) NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 200),
    notes TEXT,
    estimated_minutes INTEGER NOT NULL CHECK (typeof(estimated_minutes) = 'integer' AND estimated_minutes > 0),
    priority INTEGER NOT NULL DEFAULT 2 CHECK (typeof(priority) = 'integer' AND priority BETWEEN 1 AND 3),
    status VARCHAR(9) NOT NULL DEFAULT 'active' CHECK (status IN ('active','completed','archived')),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL CHECK (updated_at >= created_at),
    completed_at DATETIME,
    UNIQUE (id, game_id),
    CHECK ((status = 'completed' AND completed_at IS NOT NULL) OR status != 'completed'),
    CHECK (status != 'active' OR completed_at IS NULL),
    CHECK (completed_at IS NULL OR completed_at >= created_at)
);

CREATE INDEX ix_goals_game_id ON goals(game_id);

CREATE TABLE play_sessions (
    id INTEGER PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE RESTRICT,
    goal_id INTEGER NOT NULL,
    game_title_snapshot VARCHAR(200) NOT NULL CHECK (length(trim(game_title_snapshot)) BETWEEN 1 AND 200),
    goal_title_snapshot VARCHAR(200) NOT NULL CHECK (length(trim(goal_title_snapshot)) BETWEEN 1 AND 200),
    started_at DATETIME NOT NULL,
    finished_at DATETIME,
    actual_duration_minutes INTEGER CHECK (actual_duration_minutes IS NULL OR (typeof(actual_duration_minutes) = 'integer' AND actual_duration_minutes > 0)),
    enjoyment_rating INTEGER CHECK (enjoyment_rating IS NULL OR (typeof(enjoyment_rating) = 'integer' AND enjoyment_rating BETWEEN 1 AND 5)),
    progress TEXT,
    notes TEXT,
    situation_snapshot JSON NOT NULL CHECK (json_valid(situation_snapshot) AND json_type(situation_snapshot) = 'object'),
    recommendation_snapshot JSON NOT NULL CHECK (json_valid(recommendation_snapshot) AND json_type(recommendation_snapshot) = 'object'),
    FOREIGN KEY (goal_id, game_id) REFERENCES goals(id, game_id) ON DELETE RESTRICT,
    CHECK (finished_at IS NULL OR finished_at >= started_at),
    CHECK (
        (finished_at IS NULL AND actual_duration_minutes IS NULL AND enjoyment_rating IS NULL AND progress IS NULL)
        OR (finished_at IS NOT NULL AND actual_duration_minutes IS NOT NULL AND enjoyment_rating IS NOT NULL AND progress IS NOT NULL AND length(trim(progress)) > 0)
    )
);

CREATE INDEX ix_play_sessions_game_finished ON play_sessions(game_id, finished_at);
CREATE INDEX ix_play_sessions_goal_id ON play_sessions(goal_id);
CREATE UNIQUE INDEX ux_one_active_session ON play_sessions((1)) WHERE finished_at IS NULL;

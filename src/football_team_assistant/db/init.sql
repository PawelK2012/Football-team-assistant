CREATE TABLE IF NOT EXISTS players (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    rating NUMERIC(2,1) NOT NULL,
    can_play_goalkeeper BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT valid_rating
        CHECK (
            rating >= 1.0
            AND rating <= 6.0
            AND rating * 2 = FLOOR(rating * 2)
        )
);


CREATE TABLE IF NOT EXISTS fixtures (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fixture_date DATE NOT NULL,
    opponent VARCHAR(150) NOT NULL,
    home BOOLEAN NOT NULL
);


CREATE TABLE IF NOT EXISTS availability (
    fixture_id INTEGER NOT NULL
        REFERENCES fixtures(id)
        ON DELETE CASCADE,

    player_id INTEGER NOT NULL
        REFERENCES players(id)
        ON DELETE CASCADE,

    available BOOLEAN NOT NULL,

    PRIMARY KEY (fixture_id, player_id)
);


CREATE TABLE IF NOT EXISTS goalkeeper_history (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    fixture_id INTEGER NOT NULL
        REFERENCES fixtures(id)
        ON DELETE CASCADE,

    player_id INTEGER NOT NULL
        REFERENCES players(id)
        ON DELETE CASCADE,

    UNIQUE (fixture_id, player_id)
);
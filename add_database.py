import sqlite3
from pathlib import Path

DB_PATH = Path("db/inventory.db")

print("📁 Usando base:", DB_PATH.resolve())

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON;")

# ==============================
# TABLA DE HISTORIAL DE VIALES
# ==============================

conn.execute("""
CREATE TABLE IF NOT EXISTS reagent_unit_history (
    id TEXT PRIMARY KEY,

    reagent_unit_id TEXT NOT NULL,
    field TEXT NOT NULL,

    old_value TEXT,
    new_value TEXT,

    changed_at TEXT NOT NULL,
    changed_by TEXT,
    team_id TEXT,

    FOREIGN KEY(reagent_unit_id)
        REFERENCES reagent_units(id)
        ON DELETE CASCADE
);
""")

conn.execute("""
CREATE INDEX IF NOT EXISTS idx_ru_history_unit
ON reagent_unit_history(reagent_unit_id);
""")

conn.execute("""
CREATE INDEX IF NOT EXISTS idx_ru_history_date
ON reagent_unit_history(changed_at);
""")

# ==============================
# OPCIONAL: TRIGGER AUTOMÁTICO
# ==============================

conn.executescript("""
CREATE TRIGGER IF NOT EXISTS trg_reagent_units_update
AFTER UPDATE ON reagent_units
BEGIN

    INSERT INTO reagent_unit_history
    SELECT
        hex(randomblob(16)),
        NEW.id,
        'initial_volume',
        OLD.initial_volume,
        NEW.initial_volume,
        datetime('now'),
        NULL,
        NULL
    WHERE OLD.initial_volume != NEW.initial_volume;

    INSERT INTO reagent_unit_history
    SELECT
        hex(randomblob(16)),
        NEW.id,
        'status',
        OLD.status,
        NEW.status,
        datetime('now'),
        NULL,
        NULL
    WHERE OLD.status != NEW.status;

    INSERT INTO reagent_unit_history
    SELECT
        hex(randomblob(16)),
        NEW.id,
        'expiration_date',
        OLD.expiration_date,
        NEW.expiration_date,
        datetime('now'),
        NULL,
        NULL
    WHERE OLD.expiration_date != NEW.expiration_date;

END;
""")

conn.commit()
conn.close()

print("✅ Migración aplicada correctamente")

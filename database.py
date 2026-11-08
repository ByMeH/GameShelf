import sqlite3
from pathlib import Path
from typing import Any

class GameDatabase:

    SORT_COLUMNS = {
        "id": "id",
        "title": "title",
        "platform": "platform",
        "genre": "genre",
        "release_year": "release_year",
        "status": "status",
        "hours_played": "hours_played",
        "rating": "rating",
    }

    def __init__(self, db_path: str | Path = "gameshelf.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.create_table()

    def create_table(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                platform TEXT NOT NULL,
                genre TEXT NOT NULL,
                release_year INTEGER,
                status TEXT NOT NULL DEFAULT 'В планах'
                    CHECK (status IN ('В планах', 'Играю', 'Пройдена', 'Брошена')),
                hours_played REAL NOT NULL DEFAULT 0
                    CHECK (hours_played >= 0),
                rating INTEGER
                    CHECK (rating IS NULL OR rating BETWEEN 1 AND 10),
                is_deleted INTEGER NOT NULL DEFAULT 0
                    CHECK (is_deleted IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.commit()

    def add_game(
        self,
        title: str,
        platform: str,
        genre: str,
        release_year: int | None,
        status: str,
        hours_played: float,
        rating: int | None,
    ) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO games
                (title, platform, genre, release_year, status,
                 hours_played, rating)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (title, platform, genre, release_year, status, hours_played, rating),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def list_games(
        self,
        archived: bool = False,
        search: str | None = None,
        sort_by: str = "id",
        descending: bool = False,
    ) -> list[sqlite3.Row]:
        if sort_by not in self.SORT_COLUMNS:
            sort_by = "id"

        sql = "SELECT * FROM games WHERE is_deleted = ?"
        params: list[Any] = [1 if archived else 0]

        if search:
            sql += " AND (title LIKE ? OR platform LIKE ? OR genre LIKE ?)"
            pattern = "%" + search + "%"
            params.extend((pattern, pattern, pattern))

        direction = "DESC" if descending else "ASC"
        sql += " ORDER BY " + self.SORT_COLUMNS[sort_by] + " " + direction

        return self.conn.execute(sql, params).fetchall()

    def get_game(self, game_id: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM games WHERE id = ?", (game_id,)
        ).fetchone()

    def update_game(
        self,
        game_id: int,
        title: str,
        platform: str,
        genre: str,
        release_year: int | None,
        status: str,
        hours_played: float,
        rating: int | None,
    ) -> bool:
        cursor = self.conn.execute(
            """
            UPDATE games
            SET title = ?, platform = ?, genre = ?, release_year = ?,
                status = ?, hours_played = ?, rating = ?
            WHERE id = ? AND is_deleted = 0
            """,
            (
                title,
                platform,
                genre,
                release_year,
                status,
                hours_played,
                rating,
                game_id,
            ),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def archive_game(self, game_id: int) -> bool:
        cursor = self.conn.execute(
            "UPDATE games SET is_deleted = 1 WHERE id = ? AND is_deleted = 0",
            (game_id,),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def restore_game(self, game_id: int) -> bool:
        cursor = self.conn.execute(
            "UPDATE games SET is_deleted = 0 WHERE id = ? AND is_deleted = 1",
            (game_id,),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def hard_delete_game(self, game_id: int) -> bool:
        cursor = self.conn.execute(
            "DELETE FROM games WHERE id = ? AND is_deleted = 1", (game_id,)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def get_statistics(self) -> sqlite3.Row:
        return self.conn.execute(
            """
            SELECT
                COUNT(*) AS total_games,
                COUNT(rating) AS rated_games,
                ROUND(AVG(rating), 2) AS average_rating,
                ROUND(COALESCE(SUM(hours_played), 0), 1) AS total_hours,
                COALESCE(SUM(CASE WHEN status = 'Пройдена' THEN 1 ELSE 0 END), 0) AS completed
            FROM games
            WHERE is_deleted = 0
            """
        ).fetchone()

    def close(self) -> None:
        self.conn.close()

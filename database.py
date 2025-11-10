import sqlite3
from typing import List, Tuple


class Database:
    def __init__(self, db_path='spotted.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize the database with the scores table"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scores (
                    user_id TEXT PRIMARY KEY,
                    score INTEGER DEFAULT 0
                )
            ''')
            conn.commit()
    
    def get_score(self, user_id: str) -> int:
        """Get the score for a specific user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT score FROM scores WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def add_point(self, user_id: str, points: int):
        """Add points to a user's score (can be negative)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO scores (user_id, score) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET score = score + ?
            ''', (user_id, points, points))
            conn.commit()
    
    def get_leaderboard(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get the top scores, ordered by score descending"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, score FROM scores 
                ORDER BY score DESC 
                LIMIT ?
            ''', (limit,))
            return cursor.fetchall()
    
    def reset_scores(self):
        """Reset all scores to zero (use with caution!)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM scores')
            conn.commit()


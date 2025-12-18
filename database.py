import sqlite3
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, database_file='notes.db'):
        self.database_file = database_file
        self.conn = None
        self.connect()
        self.create_tables()
    
    def connect(self):
        """Connect to SQLite database"""
        try:
            self.conn = sqlite3.connect(self.database_file, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            logger.info(f"Database connected: {self.database_file}")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def create_tables(self):
        """Create tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                language TEXT DEFAULT 'en',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Notes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                note_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                content TEXT NOT NULL,
                message_type TEXT DEFAULT 'text',
                file_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                pinned INTEGER DEFAULT 0,
                source_chat_id INTEGER,
                source_chat_title TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Tags table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER,
                tag TEXT NOT NULL,
                FOREIGN KEY (note_id) REFERENCES notes(note_id) ON DELETE CASCADE,
                UNIQUE(note_id, tag)
            )
        """)
        
        # Activity log table for analytics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notes_user_id ON notes(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tags_note_id ON tags(note_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_activity_user_id ON activity_log(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_log(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_activity_action ON activity_log(action)
        """)
        
        self.conn.commit()
        logger.info("Database tables created/verified")
    
    def ensure_user(self, user_id, username, first_name, language='en'):
        """Create user if doesn't exist"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name, language)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, first_name, language))
        self.conn.commit()
    
    def set_user_language(self, user_id, language):
        """Set user's preferred language"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users
            SET language = ?
            WHERE user_id = ?
        """, (language, user_id))
        self.conn.commit()
    
    def get_user_language(self, user_id):
        """Get user's preferred language"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT language FROM users WHERE user_id = ?
        """, (user_id,))
        result = cursor.fetchone()
        return result[0] if result and result[0] else 'en'
    
    def log_user_activity(self, user_id, action, details=None):
        """Log user activity for analytics"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO activity_log (user_id, action, details, timestamp)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (user_id, action, details))
        self.conn.commit()
    
    def save_note(self, user_id, content, message_type='text', 
                  file_id=None, source_chat_id=None, source_chat_title=None):
        """Save a new note"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO notes (user_id, content, message_type, file_id, 
                             source_chat_id, source_chat_title)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, content, message_type, file_id, 
              source_chat_id, source_chat_title))
        note_id = cursor.lastrowid
        self.conn.commit()
        logger.info(f"Note {note_id} saved for user {user_id}")
        return note_id
    
    def add_tag(self, note_id, tag):
        """Add a tag to a note"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO tags (note_id, tag)
                VALUES (?, ?)
            """, (note_id, tag.lower()))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error adding tag: {e}")
            self.conn.rollback()
    
    def get_tags_for_note(self, note_id):
        """Get all tags for a note"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT tag FROM tags WHERE note_id = ?
        """, (note_id,))
        return [row[0] for row in cursor.fetchall()]
    
    def get_recent_notes(self, user_id, limit=5, offset=0):
        """Get recent notes with tags, message_type and file_id"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT note_id, content, created_at, pinned, message_type, file_id
            FROM notes
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (user_id, limit, offset))
        
        notes = []
        for row in cursor.fetchall():
            note_id = row[0]
            tags = self.get_tags_for_note(note_id)
            notes.append((row[0], row[1], row[2], row[3], row[4], row[5], tags))
        
        return notes
    
    def get_note_count(self, user_id):
        """Get total note count for user"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM notes WHERE user_id = ?
        """, (user_id,))
        return cursor.fetchone()[0]
    
    def get_note(self, note_id, user_id):
        """Get a single note with tags"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT content, created_at, pinned, message_type, file_id
            FROM notes
            WHERE note_id = ? AND user_id = ?
        """, (note_id, user_id))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        tags = self.get_tags_for_note(note_id)
        return (row[0], row[1], row[2], tags, row[3], row[4])
    
    def toggle_pin(self, note_id):
        """Toggle pin status of a note"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE notes
            SET pinned = CASE WHEN pinned = 1 THEN 0 ELSE 1 END
            WHERE note_id = ?
        """, (note_id,))
        self.conn.commit()
    
    def delete_note(self, note_id):
        """Delete a note"""
        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM notes WHERE note_id = ?
        """, (note_id,))
        self.conn.commit()
        logger.info(f"Note {note_id} deleted")
    
    def search_notes(self, user_id, query):
        """Search notes by content"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT note_id, content, created_at
            FROM notes
            WHERE user_id = ? AND content LIKE ?
            ORDER BY created_at DESC
            LIMIT 20
        """, (user_id, f'%{query}%'))
        return cursor.fetchall()
    
    def search_by_tag(self, user_id, tag):
        """Search notes by tag"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT n.note_id, n.content, n.created_at
            FROM notes n
            JOIN tags t ON n.note_id = t.note_id
            WHERE n.user_id = ? AND t.tag = ?
            ORDER BY n.created_at DESC
            LIMIT 20
        """, (user_id, tag.lower()))
        return cursor.fetchall()
    
    def search_this_week(self, user_id):
        """Get notes from this week"""
        cursor = self.conn.cursor()
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute("""
            SELECT note_id, content, created_at
            FROM notes
            WHERE user_id = ? AND created_at >= ?
            ORDER BY created_at DESC
        """, (user_id, week_ago))
        return cursor.fetchall()
    
    def get_pinned_notes(self, user_id):
        """Get all pinned notes"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT note_id, content, created_at
            FROM notes
            WHERE user_id = ? AND pinned = 1
            ORDER BY created_at DESC
        """, (user_id,))
        
        notes = []
        for row in cursor.fetchall():
            note_id = row[0]
            tags = self.get_tags_for_note(note_id)
            notes.append((row[0], row[1], row[2], tags))
        
        return notes
    
    def get_random_note(self, user_id):
        """Get a random note"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT note_id, content
            FROM notes
            WHERE user_id = ?
            ORDER BY RANDOM()
            LIMIT 1
        """, (user_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        note_id = row[0]
        tags = self.get_tags_for_note(note_id)
        return (row[0], row[1], tags)
    
    def get_popular_tags(self, user_id, limit=6):
        """Get most used tags"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT t.tag, COUNT(*) as count
            FROM tags t
            JOIN notes n ON t.note_id = n.note_id
            WHERE n.user_id = ?
            GROUP BY t.tag
            ORDER BY count DESC
            LIMIT ?
        """, (user_id, limit))
        return [row[0] for row in cursor.fetchall()]
    
    def get_user_stats(self, user_id):
        """Get user statistics"""
        cursor = self.conn.cursor()
        
        # Total notes
        cursor.execute("""
            SELECT COUNT(*) FROM notes WHERE user_id = ?
        """, (user_id,))
        total_notes = cursor.fetchone()[0]
        
        # Pinned count
        cursor.execute("""
            SELECT COUNT(*) FROM notes 
            WHERE user_id = ? AND pinned = 1
        """, (user_id,))
        pinned_count = cursor.fetchone()[0]
        
        # Unique tags
        cursor.execute("""
            SELECT COUNT(DISTINCT t.tag)
            FROM tags t
            JOIN notes n ON t.note_id = n.note_id
            WHERE n.user_id = ?
        """, (user_id,))
        unique_tags = cursor.fetchone()[0]
        
        # First note date
        cursor.execute("""
            SELECT MIN(created_at) FROM notes WHERE user_id = ?
        """, (user_id,))
        first_note = cursor.fetchone()[0]
        if first_note:
            try:
                first_note_date = datetime.fromisoformat(first_note).strftime('%B %d, %Y')
            except:
                first_note_date = 'N/A'
        else:
            first_note_date = 'N/A'
        
        # Top tags
        cursor.execute("""
            SELECT t.tag, COUNT(*) as count
            FROM tags t
            JOIN notes n ON t.note_id = n.note_id
            WHERE n.user_id = ?
            GROUP BY t.tag
            ORDER BY count DESC
            LIMIT 5
        """, (user_id,))
        top_tags = cursor.fetchall()
        
        return {
            'total_notes': total_notes,
            'pinned_count': pinned_count,
            'unique_tags': unique_tags,
            'first_note_date': first_note_date,
            'top_tags': top_tags
        }
    
    # Analytics methods
    def get_total_users(self):
        """Get total number of users"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        return cursor.fetchone()[0]
    
    def get_active_users(self, days=7):
        """Get active users in last N days"""
        cursor = self.conn.cursor()
        date_threshold = (datetime.now() - timedelta(days=days)).isoformat()
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) 
            FROM activity_log 
            WHERE timestamp >= ?
        """, (date_threshold,))
        return cursor.fetchone()[0]
    
    def get_total_notes_all_users(self):
        """Get total notes across all users"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM notes")
        return cursor.fetchone()[0]
    
    def get_notes_by_type_stats(self):
        """Get note count by message type"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT message_type, COUNT(*) as count
            FROM notes
            GROUP BY message_type
            ORDER BY count DESC
        """)
        return dict(cursor.fetchall())
    
    def get_top_users(self, limit=10):
        """Get users with most notes"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT u.user_id, u.first_name, u.username, COUNT(n.note_id) as note_count
            FROM users u
            LEFT JOIN notes n ON u.user_id = n.user_id
            GROUP BY u.user_id
            ORDER BY note_count DESC
            LIMIT ?
        """, (limit,))
        return cursor.fetchall()
    
    def get_language_distribution(self):
        """Get user count by language"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT language, COUNT(*) as count
            FROM users
            GROUP BY language
            ORDER BY count DESC
        """)
        return dict(cursor.fetchall())
    
    def get_popular_tags_global(self, limit=20):
        """Get most popular tags across all users"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT tag, COUNT(*) as count
            FROM tags
            GROUP BY tag
            ORDER BY count DESC
            LIMIT ?
        """, (limit,))
        return cursor.fetchall()
    
    def get_new_users_today(self):
        """Get number of new users today"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE DATE(created_at) = DATE('now')
        """)
        return cursor.fetchone()[0]
    
    def get_notes_created_today(self):
        """Get number of notes created today"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM notes 
            WHERE DATE(created_at) = DATE('now')
        """)
        return cursor.fetchone()[0]
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
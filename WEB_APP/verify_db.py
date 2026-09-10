import os
import sqlite3

os.chdir(r'e:\GUNAL 2025\PROJECT 2025\17.SUSPICIOUS_ACTIVITY-MULTI\WEB_APP')
db_path = 'users.db'
if not os.path.exists(db_path):
    print('users.db not found; nothing to verify.')
else:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA table_info('user')")
        rows = cur.fetchall()
        cols = [r[1] for r in rows]
        print('user table columns:', cols)
        if 'email_notifications_enabled' in cols:
            print('✅ Column email_notifications_enabled exists')
        else:
            print('❌ Column email_notifications_enabled NOT found')
            try:
                cur.execute("ALTER TABLE user ADD COLUMN email_notifications_enabled INTEGER DEFAULT 1")
                conn.commit()
                print('➕ Added column email_notifications_enabled to user table')
            except Exception as e:
                print('Failed to add column:', e)
    except Exception as e:
        print('Error querying DB:', e)
    finally:
        conn.close()

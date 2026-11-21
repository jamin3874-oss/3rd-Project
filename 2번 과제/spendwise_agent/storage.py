"""SQLite persistence; all monetary amounts are integer KRW."""
import sqlite3
from pathlib import Path

SCHEMA = '''
CREATE TABLE IF NOT EXISTS transactions (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 txn_date TEXT NOT NULL, merchant TEXT NOT NULL, amount INTEGER NOT NULL CHECK(amount>0),
 category TEXT NOT NULL, note TEXT DEFAULT '', source_id TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS budgets (
 month TEXT NOT NULL, category TEXT NOT NULL, amount INTEGER NOT NULL CHECK(amount>=0),
 PRIMARY KEY(month,category)
);
CREATE TABLE IF NOT EXISTS agent_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 command TEXT NOT NULL, tool TEXT NOT NULL, args_json TEXT NOT NULL, result_json TEXT NOT NULL
);
'''

class Storage:
    def __init__(self, path='spendwise.db'):
        self.path = str(Path(path))
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def rows(self, sql, args=()):
        return [dict(x) for x in self.conn.execute(sql, args).fetchall()]

    def write(self, sql, args=()):
        with self.conn:
            result = self.conn.execute(sql,args)
        return result.rowcount

    def log(self, command, tool, args, result):
        import json
        self.write('INSERT INTO agent_events(command,tool,args_json,result_json) VALUES(?,?,?,?)',
                   (command,tool,json.dumps(args,ensure_ascii=False),json.dumps(result,ensure_ascii=False)))

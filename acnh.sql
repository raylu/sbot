CREATE TABLE IF NOT EXISTS user (
	id TEXT PRIMARY KEY,
	username TEXT,
	code TEXT,
	timezone TEXT
);

CREATE TABLE IF NOT EXISTS sell_price (
	user_id TEXT,
	created_at TEXT,
	expiration TEXT,
	price INTEGER,
	FOREIGN KEY(user_id) REFERENCES user(id)
);

CREATE TABLE IF NOT EXISTS sell_trigger (
	user_id TEXT PRIMARY KEY,
	price INTEGER,
	FOREIGN KEY(user_id) REFERENCES user(id)
);

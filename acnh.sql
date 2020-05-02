CREATE TABLE IF NOT EXISTS user (
	id TEXT PRIMARY KEY,
	username TEXT,
	code TEXT,
	timezone TEXT
);

CREATE TABLE IF NOT EXISTS sell_price (
	user_id TEXT,
	week_local TEXT,
	week_index INTEGER,
	expiration TEXT,
	price INTEGER,
	FOREIGN KEY(user_id) REFERENCES user(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_sell_price_user_expiration
ON sell_price (user_id, expiration);

CREATE TABLE IF NOT EXISTS sell_trigger (
	user_id TEXT PRIMARY KEY,
	price INTEGER,
	FOREIGN KEY(user_id) REFERENCES user(id)
);

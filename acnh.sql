CREATE TABLE user (
	id TEXT PRIMARY KEY,
	username TEXT,
	code TEXT,
	timezone TEXT
);

CREATE TABLE sale_price (
	user_id TEXT,
	created_at TEXT,
	price INTEGER,
	FOREIGN KEY(user_id) REFERENCES user(id)
);

CREATE TABLE sell_trigger (
	user_id TEXT PRIMARY KEY,
	price INTEGER,
	FOREIGN KEY(user_id) REFERENCES user(id)
);

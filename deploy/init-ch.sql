CREATE TABLE IF NOT EXISTS default.events
(
    event_id    String,
    event_type  String,
    user_id     String,
    product_id  String,
    price       Float64,
    timestamp   DateTime,
    category    String,
    ip_address  String
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, user_id)
SETTINGS index_granularity = 8192;

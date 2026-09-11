package main

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"path"
	"regexp"
	"strconv"
	"strings"
	"time"
)

type config struct {
	host     string
	port     string
	user     string
	password string
	database string
}

type clickhouse struct {
	config config
	client *http.Client
}

func newClickHouse() *clickhouse {
	database := getenv("CH_DB", "default")
	if !identifierRE.MatchString(database) {
		database = "default"
	}
	return &clickhouse{
		config: config{
			host:     getenv("CH_HOST", "localhost"),
			port:     getenv("CH_PORT", "8123"),
			user:     getenv("CH_USER", "default"),
			password: os.Getenv("CH_PASSWORD"),
			database: database,
		},
		client: &http.Client{Timeout: 15 * time.Second},
	}
}

func getenv(name, fallback string) string {
	if value := os.Getenv(name); value != "" {
		return value
	}
	return fallback
}

func loadDotEnv(filename string) error {
	file, err := os.Open(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		name, value, ok := strings.Cut(line, "=")
		if !ok {
			continue
		}
		name = strings.TrimSpace(name)
		value = strings.Trim(strings.TrimSpace(value), `"'`)
		if name != "" && os.Getenv(name) == "" {
			if err := os.Setenv(name, value); err != nil {
				return fmt.Errorf("set %s from %s: %w", name, filename, err)
			}
		}
	}
	if err := scanner.Err(); err != nil {
		return fmt.Errorf("read %s: %w", filename, err)
	}
	return nil
}

var identifierRE = regexp.MustCompile(`^[A-Za-z_][A-Za-z0-9_]*$`)

func (db *clickhouse) table() string {
	return db.config.database + ".events"
}

func (db *clickhouse) query(ctx context.Context, statement string) ([]map[string]any, error) {
	// JSONEachRow is available through ClickHouse's HTTP interface and avoids a
	// runtime driver dependency while retaining native ClickHouse SQL semantics.
	endpoint := "http://" + db.config.host + ":" + db.config.port + "/"
	query := url.Values{}
	query.Set("database", db.config.database)
	query.Set("user", db.config.user)
	query.Set("password", db.config.password)
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint+"?"+query.Encode(),
		strings.NewReader(strings.TrimSpace(statement)+"\nFORMAT JSONEachRow"))
	if err != nil {
		return nil, err
	}
	request.Header.Set("Content-Type", "text/plain; charset=utf-8")
	response, err := db.client.Do(request)
	if err != nil {
		return nil, err
	}
	defer response.Body.Close()
	body, err := io.ReadAll(io.LimitReader(response.Body, 20<<20))
	if err != nil {
		return nil, err
	}
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		return nil, fmt.Errorf("clickhouse returned %s: %s", response.Status, strings.TrimSpace(string(body)))
	}
	if len(bytes.TrimSpace(body)) == 0 {
		return []map[string]any{}, nil
	}

	decoder := json.NewDecoder(bytes.NewReader(body))
	decoder.UseNumber()
	rows := make([]map[string]any, 0)
	for {
		var row map[string]any
		if err := decoder.Decode(&row); err != nil {
			if errors.Is(err, io.EOF) {
				break
			}
			return nil, fmt.Errorf("decode ClickHouse response: %w", err)
		}
		rows = append(rows, row)
	}
	return rows, nil
}

func sqlString(value string) string {
	value = strings.NewReplacer(
		`\`, `\\`,
		`'`, `\'`,
		"\n", `\n`,
		"\r", `\r`,
		"\x00", `\0`,
	).Replace(value)
	return "'" + value + "'"
}

func sqlEquals(column, value string) string {
	return column + " = " + sqlString(value)
}

func parseWindow(value string) (string, error) {
	windows := map[string]string{
		"1h":  "now() - INTERVAL 1 HOUR",
		"6h":  "now() - INTERVAL 6 HOUR",
		"24h": "now() - INTERVAL 24 HOUR",
		"7d":  "now() - INTERVAL 7 DAY",
		"30d": "now() - INTERVAL 30 DAY",
	}
	if expression, ok := windows[value]; ok {
		return expression, nil
	}
	return "", fmt.Errorf("window must be one of [1h 6h 24h 7d 30d]")
}

func parseBucket(value string) (string, error) {
	buckets := map[string]string{
		"minute": "toStartOfMinute",
		"hour":   "toStartOfHour",
		"day":    "toStartOfDay",
	}
	if expression, ok := buckets[value]; ok {
		return expression, nil
	}
	return "", errors.New("bucket must be one of [minute hour day]")
}

func parseIntQuery(values url.Values, key string, fallback, minimum, maximum int) (int, error) {
	raw := values.Get(key)
	if raw == "" {
		return fallback, nil
	}
	value, err := strconv.Atoi(raw)
	if err != nil || value < minimum || value > maximum {
		return 0, fmt.Errorf("%s must be between %d and %d", key, minimum, maximum)
	}
	return value, nil
}

func asFloat(value any) float64 {
	switch number := value.(type) {
	case json.Number:
		result, _ := number.Float64()
		return result
	case float64:
		return number
	case int:
		return float64(number)
	default:
		return 0
	}
}

func asInt(value any) int64 {
	switch number := value.(type) {
	case json.Number:
		result, _ := strconv.ParseInt(number.String(), 10, 64)
		if result != 0 {
			return result
		}
		floatResult, _ := number.Float64()
		return int64(floatResult)
	case float64:
		return int64(number)
	case int64:
		return number
	default:
		return 0
	}
}

func round(value float64) float64 {
	return float64(int64(value*100+0.5)) / 100
}

func formatTimestamp(value any) any {
	text, ok := value.(string)
	if !ok || text == "" || strings.Contains(text, "T") {
		return value
	}
	for _, layout := range []string{
		"2006-01-02 15:04:05.999999999",
		"2006-01-02 15:04:05",
	} {
		if parsed, err := time.ParseInLocation(layout, text, time.UTC); err == nil {
			return parsed.Format("2006-01-02T15:04:05.999999999")
		}
	}
	return value
}

func formatTimestamps(rows []map[string]any, fields ...string) {
	for _, row := range rows {
		for _, field := range fields {
			if value, ok := row[field]; ok {
				row[field] = formatTimestamp(value)
			}
		}
	}
}

func writeJSON(writer http.ResponseWriter, status int, value any) {
	writer.Header().Set("Content-Type", "application/json")
	writer.WriteHeader(status)
	_ = json.NewEncoder(writer).Encode(value)
}

func writeError(writer http.ResponseWriter, status int, err error) {
	writeJSON(writer, status, map[string]string{"detail": err.Error()})
}

func (db *clickhouse) withQueryError(writer http.ResponseWriter, query func() (any, error)) {
	result, err := query()
	if err != nil {
		status := http.StatusServiceUnavailable
		var notFound notFoundError
		if errors.As(err, &notFound) {
			status = http.StatusNotFound
		}
		writeError(writer, status, err)
		return
	}
	writeJSON(writer, http.StatusOK, result)
}

func (db *clickhouse) health(writer http.ResponseWriter, request *http.Request) {
	db.withQueryError(writer, func() (any, error) {
		rows, err := db.query(request.Context(), "SELECT count() AS total_events FROM "+db.table())
		if err != nil {
			return nil, err
		}
		var total any = int64(0)
		if len(rows) > 0 {
			total = rows[0]["total_events"]
		}
		return map[string]any{"status": "ok", "clickhouse": "connected", "total_events": total}, nil
	})
}

func (db *clickhouse) events(writer http.ResponseWriter, request *http.Request) {
	values := request.URL.Query()
	limit, err := parseIntQuery(values, "limit", 50, 1, 1000)
	if err != nil {
		writeError(writer, http.StatusBadRequest, err)
		return
	}
	offset, err := parseIntQuery(values, "offset", 0, 0, int(^uint(0)>>1))
	if err != nil {
		writeError(writer, http.StatusBadRequest, err)
		return
	}
	window := values.Get("window")
	if window == "" {
		window = "24h"
	}
	since, err := parseWindow(window)
	if err != nil {
		writeError(writer, http.StatusBadRequest, err)
		return
	}
	where := []string{"timestamp >= " + since}
	for _, filter := range []struct{ key, column string }{
		{"event_type", "event_type"},
		{"category", "category"},
		{"user_id", "user_id"},
	} {
		if value := values.Get(filter.key); value != "" {
			where = append(where, sqlEquals(filter.column, value))
		}
	}
	statement := fmt.Sprintf(`SELECT event_id, event_type, user_id, product_id,
		price, timestamp, category, ip_address
		FROM %s WHERE %s ORDER BY timestamp DESC LIMIT %d OFFSET %d`,
		db.table(), strings.Join(where, " AND "), limit, offset)
	db.withQueryError(writer, func() (any, error) {
		rows, err := db.query(request.Context(), statement)
		formatTimestamps(rows, "timestamp")
		return map[string]any{"data": rows, "limit": limit, "offset": offset}, err
	})
}

func (db *clickhouse) overview(writer http.ResponseWriter, request *http.Request) {
	window, since, err := requestedWindow(request)
	if err != nil {
		writeError(writer, http.StatusBadRequest, err)
		return
	}
	statement := fmt.Sprintf(`SELECT count() AS total_events,
		countIf(event_type = 'view') AS views, countIf(event_type = 'click') AS clicks,
		countIf(event_type = 'add_to_cart') AS carts, countIf(event_type = 'purchase') AS purchases,
		uniqExact(user_id) AS unique_users, sumIf(price, event_type = 'purchase') AS total_revenue,
		if(countIf(event_type='purchase') > 0, sumIf(price,event_type='purchase') / countIf(event_type='purchase'), 0) AS aov,
		if(countIf(event_type='view') > 0, 100.0 * countIf(event_type='purchase') / countIf(event_type='view'), 0) AS cvr_pct
		FROM %s WHERE timestamp >= %s`, db.table(), since)
	db.withQueryError(writer, func() (any, error) {
		rows, err := db.query(request.Context(), statement)
		if err != nil {
			return nil, err
		}
		result := map[string]any{"window": window}
		if len(rows) > 0 {
			for key, value := range rows[0] {
				result[key] = value
			}
		}
		return result, nil
	})
}

func requestedWindow(request *http.Request) (string, string, error) {
	window := request.URL.Query().Get("window")
	if window == "" {
		window = "24h"
	}
	since, err := parseWindow(window)
	return window, since, err
}

func (db *clickhouse) funnel(writer http.ResponseWriter, request *http.Request) {
	window, since, err := requestedWindow(request)
	if err != nil {
		writeError(writer, http.StatusBadRequest, err)
		return
	}
	values := request.URL.Query()
	category := values.Get("category")
	filter := ""
	if category != "" {
		filter = " AND " + sqlEquals("category", category)
	}
	statement := fmt.Sprintf(`SELECT countIf(event_type = 'view') AS views,
		countIf(event_type = 'click') AS clicks, countIf(event_type = 'add_to_cart') AS carts,
		countIf(event_type = 'purchase') AS purchases FROM %s
		WHERE timestamp >= %s%s`, db.table(), since, filter)
	db.withQueryError(writer, func() (any, error) {
		rows, err := db.query(request.Context(), statement)
		if err != nil {
			return nil, err
		}
		var valuesRow map[string]any
		if len(rows) > 0 {
			valuesRow = rows[0]
		} else {
			valuesRow = map[string]any{}
		}
		views, clicks := asFloat(valuesRow["views"]), asFloat(valuesRow["clicks"])
		carts, purchases := asFloat(valuesRow["carts"]), asFloat(valuesRow["purchases"])
		pct := func(numerator, denominator float64) float64 {
			if denominator == 0 {
				return 0
			}
			return round(100 * numerator / denominator)
		}
		categoryResult := any(nil)
		if _, present := values["category"]; present {
			categoryResult = category
		}
		return map[string]any{
			"window": window, "category": categoryResult,
			"stages": []map[string]any{
				{"stage": "view", "count": asCount(valuesRow["views"]), "drop_off_pct": nil},
				{"stage": "click", "count": asCount(valuesRow["clicks"]), "drop_off_pct": pct(clicks, views)},
				{"stage": "add_to_cart", "count": asCount(valuesRow["carts"]), "drop_off_pct": pct(carts, clicks)},
				{"stage": "purchase", "count": asCount(valuesRow["purchases"]), "drop_off_pct": pct(purchases, carts)},
			},
			"overall_cvr_pct": pct(purchases, views),
		}, nil
	})
}

func asCount(value any) any {
	if number, ok := value.(json.Number); ok {
		if integer, err := strconv.ParseInt(number.String(), 10, 64); err == nil {
			return integer
		}
	}
	return int64(asFloat(value))
}

func (db *clickhouse) timeseries(writer http.ResponseWriter, request *http.Request) {
	window, since, err := requestedWindow(request)
	if err != nil {
		writeError(writer, http.StatusBadRequest, err)
		return
	}
	bucket := request.URL.Query().Get("bucket")
	if bucket == "" {
		bucket = "hour"
	}
	trunc, err := parseBucket(bucket)
	if err != nil {
		writeError(writer, http.StatusBadRequest, err)
		return
	}
	filter := ""
	if eventType := request.URL.Query().Get("event_type"); eventType != "" {
		filter = " AND " + sqlEquals("event_type", eventType)
	}
	statement := fmt.Sprintf(`SELECT %s(timestamp) AS bucket, event_type, count() AS cnt,
		sumIf(price, event_type = 'purchase') AS revenue FROM %s
		WHERE timestamp >= %s%s GROUP BY bucket, event_type ORDER BY bucket ASC, event_type`,
		trunc, db.table(), since, filter)
	db.withQueryError(writer, func() (any, error) {
		rows, err := db.query(request.Context(), statement)
		formatTimestamps(rows, "bucket")
		return map[string]any{"window": window, "bucket": bucket, "data": rows}, err
	})
}

func (db *clickhouse) topProducts(writer http.ResponseWriter, request *http.Request) {
	window, since, err := requestedWindow(request)
	if err != nil {
		writeError(writer, http.StatusBadRequest, err)
		return
	}
	by := request.URL.Query().Get("by")
	if by == "" {
		by = "revenue"
	}
	order, ok := map[string]string{"views": "views DESC", "purchases": "purchases DESC", "revenue": "revenue DESC"}[by]
	if !ok {
		writeError(writer, http.StatusBadRequest, errors.New("by must be one of [views purchases revenue]"))
		return
	}
	limit, err := parseIntQuery(request.URL.Query(), "limit", 10, 1, 100)
	if err != nil {
		writeError(writer, http.StatusBadRequest, err)
		return
	}
	statement := fmt.Sprintf(`SELECT product_id, category, countIf(event_type = 'view') AS views,
		countIf(event_type = 'click') AS clicks, countIf(event_type = 'add_to_cart') AS carts,
		countIf(event_type = 'purchase') AS purchases, sumIf(price,event_type='purchase') AS revenue,
		if(countIf(event_type='view') > 0, 100.0 * countIf(event_type='purchase') / countIf(event_type='view'), 0) AS cvr_pct
		FROM %s WHERE timestamp >= %s GROUP BY product_id, category ORDER BY %s LIMIT %d`,
		db.table(), since, order, limit)
	db.withQueryError(writer, func() (any, error) {
		rows, err := db.query(request.Context(), statement)
		return map[string]any{"window": window, "by": by, "data": rows}, err
	})
}

func (db *clickhouse) topCategories(writer http.ResponseWriter, request *http.Request) {
	window, since, err := requestedWindow(request)
	if err != nil {
		writeError(writer, http.StatusBadRequest, err)
		return
	}
	statement := fmt.Sprintf(`SELECT category, countIf(event_type = 'view') AS views,
		countIf(event_type = 'click') AS clicks, countIf(event_type = 'add_to_cart') AS carts,
		countIf(event_type = 'purchase') AS purchases, sumIf(price,event_type='purchase') AS revenue,
		if(countIf(event_type='view') > 0, 100.0 * countIf(event_type='purchase') / countIf(event_type='view'), 0) AS cvr_pct,
		if(countIf(event_type='purchase') > 0, sumIf(price,event_type='purchase') / countIf(event_type='purchase'), 0) AS aov
		FROM %s WHERE timestamp >= %s GROUP BY category ORDER BY revenue DESC`, db.table(), since)
	db.withQueryError(writer, func() (any, error) {
		rows, err := db.query(request.Context(), statement)
		return map[string]any{"window": window, "data": rows}, err
	})
}

func (db *clickhouse) userJourney(writer http.ResponseWriter, request *http.Request, userID string) {
	window := request.URL.Query().Get("window")
	if window == "" {
		window = "7d"
	}
	since, err := parseWindow(window)
	if err != nil {
		writeError(writer, http.StatusBadRequest, err)
		return
	}
	safeUserID := sqlEquals("user_id", userID)
	summaryStatement := fmt.Sprintf(`SELECT count() AS total_events, countIf(event_type = 'view') AS views,
		countIf(event_type = 'click') AS clicks, countIf(event_type = 'add_to_cart') AS carts,
		countIf(event_type = 'purchase') AS purchases, sumIf(price,event_type='purchase') AS total_spent,
		uniqExact(product_id) AS unique_products_viewed, min(timestamp) AS first_seen,
		max(timestamp) AS last_seen FROM %s WHERE %s AND timestamp >= %s`,
		db.table(), safeUserID, since)
	eventsStatement := fmt.Sprintf(`SELECT event_id, event_type, product_id, price, timestamp, category
		FROM %s WHERE %s AND timestamp >= %s ORDER BY timestamp ASC LIMIT 200`,
		db.table(), safeUserID, since)
	db.withQueryError(writer, func() (any, error) {
		summaryRows, err := db.query(request.Context(), summaryStatement)
		if err != nil {
			return nil, err
		}
		if len(summaryRows) == 0 || asInt(summaryRows[0]["total_events"]) == 0 {
			return nil, notFoundError{message: fmt.Sprintf("No events found for user '%s'", userID)}
		}
		summary := summaryRows[0]
		formatTimestamps([]map[string]any{summary}, "first_seen", "last_seen")
		eventRows, err := db.query(request.Context(), eventsStatement)
		if err != nil {
			return nil, err
		}
		formatTimestamps(eventRows, "timestamp")
		return map[string]any{"user_id": userID, "window": window, "summary": summary, "events": eventRows}, nil
	})
}

type notFoundError struct{ message string }

func (err notFoundError) Error() string { return err.message }

func (db *clickhouse) revenue(writer http.ResponseWriter, request *http.Request) {
	window, since, err := requestedWindow(request)
	if err != nil {
		writeError(writer, http.StatusBadRequest, err)
		return
	}
	bucket := request.URL.Query().Get("bucket")
	if bucket == "" {
		bucket = "hour"
	}
	trunc, err := parseBucket(bucket)
	if err != nil {
		writeError(writer, http.StatusBadRequest, err)
		return
	}
	statement := fmt.Sprintf(`SELECT %s(timestamp) AS bucket, count() AS orders,
		sum(price) AS revenue, avg(price) AS aov FROM %s
		WHERE event_type = 'purchase' AND timestamp >= %s
		GROUP BY bucket ORDER BY bucket ASC`, trunc, db.table(), since)
	db.withQueryError(writer, func() (any, error) {
		rows, err := db.query(request.Context(), statement)
		if err != nil {
			return nil, err
		}
		formatTimestamps(rows, "bucket")
		var totalRevenue float64
		var totalOrders int64
		for _, row := range rows {
			totalRevenue += asFloat(row["revenue"])
			totalOrders += asInt(row["orders"])
		}
		overallAOV := float64(0)
		if totalOrders > 0 {
			overallAOV = totalRevenue / float64(totalOrders)
		}
		return map[string]any{
			"window": window, "bucket": bucket,
			"total_revenue": round(totalRevenue), "total_orders": totalOrders,
			"overall_aov": round(overallAOV), "timeseries": rows,
		}, nil
	})
}

func (db *clickhouse) realtime(writer http.ResponseWriter, request *http.Request) {
	statement := fmt.Sprintf(`SELECT toStartOfMinute(timestamp) AS bucket,
		countIf(event_type = 'view') AS views, countIf(event_type = 'click') AS clicks,
		countIf(event_type = 'add_to_cart') AS carts, countIf(event_type = 'purchase') AS purchases,
		count() AS total FROM %s WHERE timestamp >= now() - INTERVAL 2 MINUTE
		GROUP BY bucket ORDER BY bucket ASC`, db.table())
	db.withQueryError(writer, func() (any, error) {
		rows, err := db.query(request.Context(), statement)
		if err != nil {
			return nil, err
		}
		formatTimestamps(rows, "bucket")
		eps := float64(0)
		if len(rows) > 0 {
			eps = round(asFloat(rows[len(rows)-1]["total"]) / 60)
		}
		return map[string]any{"events_per_sec": eps, "buckets": rows}, nil
	})
}

func (db *clickhouse) handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", db.health)
	mux.HandleFunc("/events", db.events)
	mux.HandleFunc("/metrics/overview", db.overview)
	mux.HandleFunc("/metrics/funnel", db.funnel)
	mux.HandleFunc("/metrics/timeseries", db.timeseries)
	mux.HandleFunc("/metrics/top-products", db.topProducts)
	mux.HandleFunc("/metrics/top-categories", db.topCategories)
	mux.HandleFunc("/metrics/revenue", db.revenue)
	mux.HandleFunc("/metrics/realtime", db.realtime)
	mux.HandleFunc("/metrics/users/", func(writer http.ResponseWriter, request *http.Request) {
		userID := strings.TrimPrefix(request.URL.Path, "/metrics/users/")
		if userID == "" || strings.Contains(userID, "/") {
			writeError(writer, http.StatusNotFound, errors.New("user not found"))
			return
		}
		userID, err := url.PathUnescape(path.Clean("/" + userID)[1:])
		if err != nil {
			writeError(writer, http.StatusBadRequest, err)
			return
		}
		db.userJourney(writer, request, userID)
	})
	return cors(mux)
}

func cors(next http.Handler) http.Handler {
	return http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		writer.Header().Set("Access-Control-Allow-Origin", "*")
		writer.Header().Set("Access-Control-Allow-Methods", "GET")
		writer.Header().Set("Access-Control-Allow-Headers", "*")
		if request.Method == http.MethodOptions {
			writer.WriteHeader(http.StatusNoContent)
			return
		}
		if request.Method != http.MethodGet {
			writeError(writer, http.StatusMethodNotAllowed, errors.New("method not allowed"))
			return
		}
		next.ServeHTTP(writer, request)
	})
}

func main() {
	if err := loadDotEnv(".env"); err != nil && !errors.Is(err, os.ErrNotExist) {
		log.Fatalf("load .env: %v", err)
	}
	db := newClickHouse()
	addr := getenv("API_ADDR", ":8000")
	log.Printf("WebStream Analytics API listening on %s (ClickHouse %s:%s)", addr, db.config.host, db.config.port)
	if err := http.ListenAndServe(addr, db.handler()); err != nil {
		log.Fatal(err)
	}
}

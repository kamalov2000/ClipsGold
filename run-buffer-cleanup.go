package main

import (
	"context"
	"fmt"
	"os"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

func main() {
	// Настройте строку подключения к вашей БД
	connStr := fmt.Sprintf(
		"host=%s port=%s dbname=%s user=%s password=%s sslmode=disable",
		getEnv("PURCHASE_REPORT_HOST", "purchase-pg-dev-haproxy-hisamutdinov-r18.purchase.k8s.portal-dev-el"),
		getEnv("PURCHASE_REPORT_MASTER_PORT", "5000"),
		getEnv("PURCHASE_REPORT_DB", "reports"),
		getEnv("PURCHASE_REPORT_USER", "dbuser"),
		getEnv("PURCHASE_REPORT_PASSWORD", "CHMmnkBYdbKic1mhgnbuWuUDOhpjVwxL"),
	)

	pool, err := pgxpool.New(context.Background(), connStr)
	if err != nil {
		fmt.Printf("Unable to connect to database: %v\n", err)
		os.Exit(1)
	}
	defer pool.Close()

	fmt.Println("Starting buffer cleanup job...")

	ticker := time.NewTicker(10 * time.Minute)
	defer ticker.Stop()

	// Первый запуск сразу
	runCleanup(pool)

	// Затем каждые 10 минут
	for range ticker.C {
		runCleanup(pool)
	}
}

func runCleanup(pool *pgxpool.Pool) {
	ctx := context.Background()

	fmt.Printf("[%s] Running buffer cleanup...\n", time.Now().Format("2006-01-02 15:04:05"))

	_, err := pool.Exec(ctx, `CALL stock_control.buffer_goods_return_shk_clear_expired();`)
	if err != nil {
		fmt.Printf("[ERROR] Failed to cleanup buffer: %v\n", err)
		return
	}

	fmt.Printf("[%s] Buffer cleanup completed successfully\n", time.Now().Format("2006-01-02 15:04:05"))
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

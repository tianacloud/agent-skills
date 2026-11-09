package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"os"
	"time"

	"github.com/tianacloud/sdk-go/files"
	"github.com/tianacloud/sdk-go/function"
)

func main() {
	http.HandleFunc("/generate", func(w http.ResponseWriter, r *http.Request) {
		caller, ok := function.CallerFromRequest(r)
		if !ok || !caller.IsAppOwner() {
			http.Error(w, "仅 App 作者可执行", http.StatusForbidden)
			return
		}
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", "POST")
			http.Error(w, "需要 POST", http.StatusMethodNotAllowed)
			return
		}
		config, err := function.ReadConfig()
		if err != nil {
			http.Error(w, "读取业务配置失败", http.StatusInternalServerError)
			return
		}
		webID, err := config.GetContext(r.Context(), "REPORT_WEB_ID")
		if err != nil {
			http.Error(w, "请配置 REPORT_WEB_ID", http.StatusInternalServerError)
			return
		}
		result, err := generateReport(webID)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadGateway)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(result)
	})
	if err := http.ListenAndServe(":"+os.Getenv("PORT"), nil); err != nil {
		panic(err)
	}
}

// generateReport can also be called by a business job without an HTTP request.
func generateReport(webID string) (map[string]any, error) {
	client, err := function.FilesByWebApp(webID)
	if err != nil {
		return nil, err
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	const path = "reports/task.txt"
	content := []byte("generated report\n")
	receipt, err := client.Put(ctx, path, bytes.NewReader(content), files.PutOptions{
		Size: int64(len(content)), ContentType: "text/plain; charset=utf-8", Overwrite: true,
	})
	if err == nil {
		return map[string]any{"state": "written", "receipt": receipt}, nil
	}
	var fileErr *files.Error
	if !errors.As(err, &fileErr) || fileErr.Outcome != "unknown" || fileErr.WriteID == "" {
		return nil, err
	}
	// Inspect the current object once. A failed write is never automatically replayed.
	checkCtx, checkCancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer checkCancel()
	metadata, checkErr := client.Metadata(checkCtx, path)
	if checkErr == nil && metadata.WriteID == fileErr.WriteID && metadata.Size == int64(len(content)) {
		return map[string]any{"state": "current_object_matches", "metadata": metadata}, nil
	}
	return nil, fmt.Errorf("写入结果未确认，请按业务状态处理；write_id=%s delete_confirmed=%t: %w", fileErr.WriteID, fileErr.DeleteConfirmed, err)
}

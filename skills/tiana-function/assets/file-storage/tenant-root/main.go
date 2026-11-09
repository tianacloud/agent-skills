package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"

	"github.com/tianacloud/sdk-go/files"
	"github.com/tianacloud/sdk-go/function"
)

func main() {
	http.HandleFunc("/file-demo", func(w http.ResponseWriter, r *http.Request) {
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
		result, err := exercise(function.ContextFromRequest(r))
		if err != nil {
			status := http.StatusBadGateway
			var fileErr *files.Error
			if errors.As(err, &fileErr) {
				switch fileErr.Code {
				case "FILE_EXISTS":
					status = http.StatusConflict
				case "FILE_WRITE_BLOCKED":
					status = http.StatusForbidden
				}
			}
			http.Error(w, err.Error(), status)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(result)
	})
	if err := http.ListenAndServe(":"+os.Getenv("PORT"), nil); err != nil {
		panic(err)
	}
}

func exercise(ctx context.Context) (map[string]any, error) {
	client := function.Files()
	capabilities, err := client.Capabilities(ctx)
	if err != nil {
		return nil, err
	}
	path := fmt.Sprintf("file-demo/%d.txt", time.Now().UnixNano())
	content := []byte("tenant root file\n")
	receipt, err := client.Put(ctx, path, bytes.NewReader(content), files.PutOptions{
		Size: int64(len(content)), ContentType: "text/plain; charset=utf-8",
	})
	if err != nil {
		return nil, err
	}
	metadata, err := client.Metadata(ctx, receipt.Path)
	if err != nil {
		return nil, err
	}
	listed := 0
	for cursor := ""; ; {
		page, err := client.List(ctx, "file-demo/", files.ListOptions{Cursor: cursor})
		if err != nil {
			return nil, err
		}
		listed += len(page.Entries)
		if page.NextCursor == "" {
			break
		}
		cursor = page.NextCursor
	}
	response, err := client.Get(ctx, receipt.Path, files.GetOptions{})
	if err != nil {
		return nil, err
	}
	read, readErr := io.Copy(io.Discard, response.Body)
	closeErr := response.Body.Close()
	if err := errors.Join(readErr, closeErr); err != nil {
		return nil, err
	}
	if err := client.Delete(ctx, receipt.Path); err != nil {
		return nil, err
	}
	return map[string]any{
		"capabilities": capabilities, "written": receipt, "metadata": metadata,
		"listed": listed, "read_bytes": read, "deleted": true,
	}, nil
}

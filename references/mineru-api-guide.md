# MinerU API Reference

## API Flow (Local File Upload)

MinerU v4 API local file upload differs from URL submission:

```
1. POST /api/v4/file-urls/batch
   Body: {"files": [{"name": "file.pdf"}], "model_version": "vlm"}
   Response: {"data": {"batch_id": "xxx", "file_urls": ["presigned_url"]}}

2. PUT presigned_url  (upload file, no Content-Type header)
   → System auto-submits extraction task, no manual submit needed

3. GET /api/v4/extract-results/batch/{batch_id}  (poll results)
   Response: {"data": {"extract_result": [{"state": "done", "full_zip_url": "..."}]}}
```

## API Pitfalls

1. **Request body format**: `/api/v4/file-urls/batch` `files` field is object array `[{"name": "xxx.pdf"}]`, not string array `["xxx.pdf"]`. Old `file_names` param is deprecated.
2. **Auto-submit**: After uploading to presigned URL, the system **auto-submits** the extraction task. Do not call `/api/v4/extract/task`. Manual submission creates duplicate tasks.
3. **Batch result field**: Task list is in `data.extract_result` (not `data.task_results` or `data.results`).
4. **Upload Content-Type**: Do not set Content-Type header on PUT upload. Let requests auto-handle it.
5. **model_version vs layout_model**: `model_version` controls extraction engine (`pipeline`/`vlm`/`MinerU-HTML`), `layout_model` controls layout analysis model (`doclayout_yolo` fast/`layoutlmv3` precise). Scripts use `model_version`.

## Available Parameters

| Parameter | Description | Options |
|-----------|-------------|---------|
| `model_version` | Extraction engine | `pipeline` (fast) / `vlm` (recommended) / `MinerU-HTML` |
| `layout_model` | Layout analysis | `doclayout_yolo` (fast) / `layoutlmv3` (precise) |
| `enable_formula` | Formula recognition | `true`/`false` (default true) |
| `enable_table` | Table recognition | `true`/`false` (default true) |
| `language` | Language | `auto`/`ch`/`en` |

## Limits

- Single file ≤ 200MB, ≤ 200 pages
- First 1000 pages per day at high priority, then lower priority
- Presigned URL validity: 24 hours

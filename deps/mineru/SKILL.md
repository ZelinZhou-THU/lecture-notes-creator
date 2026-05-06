---
name: mineru
description: 用 MinerU API 解析 PDF/Word/PPT/图片为 Markdown，支持公式、表格、OCR。适用于论文解析、文档提取。
---

# 📄 MinerU - 文档解析神器

**OpenDataLab 出品**

> PDF/Word/PPT/图片 → 结构化 Markdown，公式表格全保留！

---

## 🔗 资源链接

| 资源 | 链接 |
|------|------|
| **官网** | https://mineru.net/ |
| **API 文档** | https://mineru.net/apiManage/docs |
| **GitHub** | https://github.com/opendatalab/MinerU |

---

## 🎯 功能

### 支持的文件类型

| 类型 | 格式 |
|------|------|
| 📕 **PDF** | 论文、书籍、扫描件 |
| 📝 **Word** | .docx |
| 📊 **PPT** | .pptx |
| 🖼️ **图片** | .jpg, .png (OCR) |

### 核心优势

1. **公式完美保留** - LaTeX 格式输出
2. **表格结构识别** - 复杂表格也能搞定
3. **多语言 OCR** - 中英文混排无压力
4. **版面分析** - 多栏、图文混排自动处理

---

## 🛠️ Python 脚本 (推荐)

`scripts/mineru_extract.py` 是封装好的通用 MinerU API 客户端，支持 CLI 和 library 两种使用方式。

### 依赖

```bash
pip install requests
```

### CLI 使用

```bash
# 本地文件 (自动上传)
python scripts/mineru_extract.py paper.pdf --output ./out

# 远程 URL
python scripts/mineru_extract.py "https://arxiv.org/pdf/2410.17247" --output ./paper

# 指定模式和语言
python scripts/mineru_extract.py paper.pdf --mode vlm --language ch

# 禁用公式/表格识别
python scripts/mineru_extract.py paper.pdf --no-formula --no-table
```

### Library 使用

```python
import sys
sys.path.insert(0, "path/to/lecture-notes-creator/scripts")

from mineru_extract import MinerU

client = MinerU()  # 自动从 .env 或环境变量读取 MINERU_TOKEN

# 单文件提取
md_path = client.extract("paper.pdf", output_dir="./out", mode="vlm")

# URL 提取
md_path = client.extract("https://arxiv.org/pdf/2410.17247", mode="vlm")

# 批量提取
results = client.extract_batch(["a.pdf", "b.pdf"], output_base_dir="./batch")
for file_path, md_path in results:
    print(f"{file_path} → {md_path}")
```

### 也可直接调用底层函数

```python
from mineru_extract import upload_local_file, poll_batch_results, download_and_extract

batch_id = upload_local_file("paper.pdf", model_version="vlm")
results = poll_batch_results(batch_id, timeout=600)
md_path = download_and_extract(results[0], "./out")
```

### 认证

脚本自动从项目根目录 `.env` 文件或环境变量 `MINERU_TOKEN` 读取 API key：

```bash
# 方式 1: 项目根目录 .env 文件
echo "MINERU_TOKEN=your_key_here" >> .env

# 方式 2: 环境变量
export MINERU_TOKEN=your_key_here
```

### 输出结构

```
output/
├── full.md              # 完整 Markdown (公式 LaTeX, 表格 HTML)
├── content_list.json    # 结构化内容块
├── layout.json          # 版面分析结果
├── images/              # 提取的嵌入图片
└── *_model.json         # 模型处理详情
```

---

## 🚀 API 参考 (v4)

### 认证

```bash
Authorization: Bearer {YOUR_API_KEY}
```

### 本地文件上传流程

```bash
# 1. 申请上传链接 (系统自动提交解析任务)
curl -X POST "https://mineru.net/api/v4/file-urls/batch" \
  -H "Authorization: Bearer $MINERU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"files": [{"name":"paper.pdf"}], "model_version": "vlm"}'

# 返回: {"data": {"batch_id": "xxx", "file_urls": ["presigned_url"]}}

# 2. 上传文件 (无需 Content-Type)
curl -X PUT -T paper.pdf "presigned_url"

# 3. 轮询批量结果
curl "https://mineru.net/api/v4/extract-results/batch/{batch_id}" \
  -H "Authorization: Bearer $MINERU_TOKEN"
```

### URL 解析流程

```bash
# 1. 提交任务
curl -X POST "https://mineru.net/api/v4/extract/task" \
  -H "Authorization: Bearer $MINERU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://arxiv.org/pdf/2410.17247", "model_version": "vlm"}'

# 返回: {"data": {"task_id": "xxx"}}

# 2. 轮询单任务
curl "https://mineru.net/api/v4/extract/task/{task_id}" \
  -H "Authorization: Bearer $MINERU_TOKEN"

# 返回: {"data": {"state": "done", "full_zip_url": "..."}}
```

### 任务状态

| 状态 | 说明 |
|------|------|
| `pending` | 排队中 |
| `running` | 处理中 |
| `converting` | 格式转换 |
| `done` | 完成 |
| `failed` | 失败 |

---

## ⚙️ 参数说明

| 参数 | 类型 | 说明 |
|------|------|------|
| `url` | string | 文件 URL (仅 URL 模式) |
| `model_version` | string | `pipeline` / `vlm` / `MinerU-HTML` |
| `enable_formula` | bool | 启用公式识别 (默认 true) |
| `enable_table` | bool | 启用表格识别 (默认 true) |
| `layout_model` | string | `doclayout_yolo` (快) / `layoutlmv3` (准) |
| `language` | string | `auto` / `ch` / `en` |

### 模型版本对比

| 版本 | 速度 | 准确度 | 适用场景 |
|------|------|--------|----------|
| `pipeline` | 快 | 高 | 常规文档 |
| `vlm` | 慢 | 最高 | 复杂版面、公式多 |
| `MinerU-HTML` | 快 | 高 | 网页样式输出 |

---

## ⚠️ 限制

| 限制 | 数值 |
|------|------|
| 单文件大小 | 200 MB |
| 单文件页数 | 200 页 |
| 每日高优先级额度 | 1000 页 |
| 单次批量上传 | ≤50 文件 |
| 上传链接有效期 | 24 小时 |

---

## 📚 相关资源

| 资源 | 链接 |
|------|------|
| 官网 | https://mineru.net/ |
| API 文档 | https://mineru.net/apiManage/docs |
| GitHub | https://github.com/opendatalab/MinerU |

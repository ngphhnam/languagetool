# LanguageTool Service - Grammar Check

Service sử dụng LanguageTool để kiểm tra ngữ pháp và chính tả.

## Cài đặt

### Bước 1: Chuẩn bị Python service

**Yêu cầu:**
- Python 3.11+
- Java 8+ (để chạy LanguageTool server riêng)

```bash
cd services/languagetool
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt
```

### Bước 2: Khởi chạy LanguageTool Java server (bắt buộc)

Service chỉ hoạt động khi bạn tự host LanguageTool. Download và chạy server:

```bash
# Download LanguageTool
wget https://languagetool.org/download/LanguageTool-6.0.zip
unzip LanguageTool-6.0.zip
cd LanguageTool-6.0

# Chạy server (nên dùng port 8011 để tránh conflict với Python service trên 8010)
java -cp languagetool-server.jar org.languagetool.server.HTTPServer --port 8011 --public
```

Sau đó set environment variable để Python service biết cách kết nối:
```bash
export LANGTOOL_SERVER=http://localhost:8011
```

**Lưu ý:** 
- Java server chạy trên port **8011** (để tránh xung đột với Python service)
- Python service chạy trên port **8010** (API sẽ kết nối tới đây)
- Python service sẽ tự động kết nối tới Java server trên port 8011

## Cấu hình

### Environment Variable

- `LANGTOOL_SERVER`: URL của LanguageTool server (mặc định `http://localhost:8011`). Python service chạy trên 8010 và sẽ proxy request tới server này.

### Ví dụ:

```bash
export LANGTOOL_SERVER=http://localhost:8011
```

**Windows PowerShell:**
```powershell
$env:LANGTOOL_SERVER="http://localhost:8011"
```

## Chạy Service

### Cách 1: Dùng script helper (Khuyến nghị)

**Windows PowerShell:**
```powershell
.\run.ps1
```

Script này sẽ tự động:
- Tạo/activate virtual environment
- Set biến môi trường `LANGTOOL_SERVER=http://localhost:8011`
- Chạy service trên port 8010

### Cách 2: Chạy thủ công
```powershell
# Set environment variable
$env:LANGTOOL_SERVER="http://localhost:8011"

# Activate venv và chạy
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
```

## API Endpoints

### POST /v2/check

Kiểm tra ngữ pháp và chính tả.

**Request (form-data):**
- `text`: Text cần kiểm tra
- `language`: Language code (mặc định: `en-US`)

**Response:**
```json
{
  "language": {
    "name": "English (US)",
    "code": "en-US"
  },
  "matches": [
    {
      "message": "Possible spelling mistake found",
      "shortMessage": "Spelling",
      "replacements": [{"value": "correct"}],
      "offset": 0,
      "length": 5,
      "rule": {
        "id": "MORFOLOGIK_RULE_EN_US",
        "description": "Possible spelling mistake"
      }
    }
  ]
}
```

## Supported Languages

- `en-US` - English (US)
- `en-GB` - English (UK)
- `en-AU` - English (Australia)
- `en-NZ` - English (New Zealand)
- `en-ZA` - English (South Africa)
- `en-CA` - English (Canada)

## Troubleshooting

### Lỗi: LanguageTool initialization failed

**Nguyên nhân:** Java chưa được cài đặt hoặc LanguageTool không thể khởi tạo.

**Cách sửa:**
1. Cài đặt Java:
   ```bash
   # Windows: Download từ https://www.java.com
   # Linux:
   sudo apt-get install default-jdk
   # Mac:
   brew install openjdk
   ```

2. Hoặc dùng server mode:
   ```bash
   # Chạy Java server trên port 8011
   java -cp languagetool-server.jar org.languagetool.server.HTTPServer --port 8011 --public
   
   # Set environment variable
   export LANGTOOL_SERVER=http://localhost:8011
   ```

### Lỗi: Connection refused (Server mode)

**Cách sửa:**
1. Kiểm tra LanguageTool Java server đang chạy:
   ```bash
   curl http://localhost:8011/v2/languages
   ```

2. Khởi động Java server (trên port 8011):
   ```bash
   java -cp languagetool-server.jar org.languagetool.server.HTTPServer --port 8011 --public
   ```

3. Đảm bảo Python service có set environment variable:
   ```bash
   export LANGTOOL_SERVER=http://localhost:8011
   ```




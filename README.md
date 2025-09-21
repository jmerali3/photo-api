# photo-api

FastAPI service that issues S3 presigned uploads and starts Temporal workflows for image processing.

## 🔐 Authentication
All endpoints except `/healthz` require API key authentication via Bearer token:
```
Authorization: Bearer <your-api-key>
```

## Endpoints
- `GET /healthz` → health check (no auth required)
- `POST /uploads/init` → returns a presigned POST (url + fields + key) 🔐
- `POST /jobs/from-upload` → starts a workflow for an uploaded S3 object 🔐
- `POST /jobs/from-url` → starts a workflow that fetches from a URL 🔐
- `GET /jobs/{job_id}` → get status/result 🔐

## Quick start (local)

### 1. Generate API Key
```bash
python generate_api_key.py
```

### 2. Set up environment
```bash
cp .env.example .env
# Edit .env with your AWS credentials and the generated API key
```

### 3. Install dependencies and run
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --env-file .dev.env
```

### 4. Test with example client
```bash
# Update API_KEY in example_client.py with your generated key
python example_client.py
```

## 🌐 CORS Configuration

For **local client → hosted backend**, CORS is configured to allow:
- `http://localhost:3000` (React dev server)
- `http://localhost:8080` (alternative dev port)
- `http://127.0.0.1:3000`
- `http://127.0.0.1:8080`

Update `CORS_ORIGINS` in your environment file to match your client URLs.

## 🔒 Security Features

- **API Key Authentication**: Bearer token authentication for all protected endpoints
- **CORS Protection**: Configurable origins, no wildcard in production
- **Security Headers**: X-Frame-Options, CSP, XSS protection, etc.
- **Input Validation**: Pydantic models validate all requests
- **File Type Restrictions**: Only allowed image MIME types accepted

## Client Usage Example

```python
import requests

headers = {
    "Authorization": "Bearer your-api-key-here",
    "Content-Type": "application/json"
}

# Initialize upload
response = requests.post(
    "https://your-api-domain.com/uploads/init",
    headers=headers,
    json={
        "content_type": "image/jpeg",
        "max_bytes": 5000000,
        "key_prefix": "user-uploads"
    }
)

upload_data = response.json()
# Use upload_data['url'] and upload_data['fields'] for direct S3 upload
```
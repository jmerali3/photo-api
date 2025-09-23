# Infrastructure Setup for Photo API

This document outlines the minimal AWS infrastructure needed to run the photo-api in production.

## 📋 Infrastructure Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Your Client   │───▶│   EC2 Instance  │───▶│   S3 Buckets    │
│  (Local/Remote) │    │   (photo-api)   │    │  (Raw/Processed)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ PostgreSQL DB   │    │ Temporal Cloud  │
                       │ (Job Metadata)  │    │   (Workflows)   │
                       └─────────────────┘    └─────────────────┘
```

## 🏗️ Required AWS Resources

### 1. **S3 Buckets** (File Storage)
- **Raw bucket**: Stores uploaded images
- **Processed bucket**: Stores processed/transformed images

### 2. **EC2 Instance** (API Server)
- Single instance running the FastAPI application
- Includes PostgreSQL database for job logging
- No load balancer needed for single-user app

### 3. **PostgreSQL Database** (Job Metadata)
- Logs all jobs sent to Temporal with metadata
- Tracks filenames, dates, status, and results
- Can be on same EC2 or separate RDS instance

### 4. **IAM Role & Policies** (Permissions)
- EC2 instance role with S3 access
- Secure, least-privilege permissions

### 5. **Security Group** (Firewall)
- Inbound rules for API access
- PostgreSQL port (if using separate RDS)
- Minimal exposure

### 6. **Temporal** (Workflow Engine)
- Temporal Cloud (recommended) or self-hosted

---

## 📦 S3 Infrastructure

### Create S3 Buckets

```bash
# Raw images bucket
aws s3 mb s3://your-company-photos-raw-prod --region us-west-2

# Processed images bucket
aws s3 mb s3://your-company-photos-processed-prod --region us-west-2
```

### S3 Bucket Policies

**Raw Bucket Policy** (`your-company-photos-raw-prod`):
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowEC2InstanceAccess",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::YOUR_ACCOUNT_ID:role/PhotoApiEC2Role"
            },
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:GetObjectVersion"
            ],
            "Resource": "arn:aws:s3:::your-company-photos-raw-prod/*"
        },
        {
            "Sid": "AllowListBucket",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::YOUR_ACCOUNT_ID:role/PhotoApiEC2Role"
            },
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s3:::your-company-photos-raw-prod"
        }
    ]
}
```

**Processed Bucket Policy** (`your-company-photos-processed-prod`):
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowEC2InstanceAccess",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::YOUR_ACCOUNT_ID:role/PhotoApiEC2Role"
            },
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:GetObjectVersion"
            ],
            "Resource": "arn:aws:s3:::your-company-photos-processed-prod/*"
        },
        {
            "Sid": "AllowListBucket",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::YOUR_ACCOUNT_ID:role/PhotoApiEC2Role"
            },
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s3:::your-company-photos-processed-prod"
        }
    ]
}
```

### S3 Bucket Configuration

**Enable versioning** (recommended for data protection):
```bash
aws s3api put-bucket-versioning \
    --bucket your-company-photos-raw-prod \
    --versioning-configuration Status=Enabled

aws s3api put-bucket-versioning \
    --bucket your-company-photos-processed-prod \
    --versioning-configuration Status=Enabled
```

**Block public access** (security):
```bash
aws s3api put-public-access-block \
    --bucket your-company-photos-raw-prod \
    --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

---

## 🔐 IAM Setup

### 1. Create EC2 Instance Role

**Trust Policy** (`ec2-trust-policy.json`):
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "ec2.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

**Create the role**:
```bash
aws iam create-role \
    --role-name PhotoApiEC2Role \
    --assume-role-policy-document file://ec2-trust-policy.json
```

### 2. Create IAM Policy for S3 Access

**S3 Access Policy** (`photo-api-s3-policy.json`):
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowS3BucketAccess",
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:GetBucketLocation"
            ],
            "Resource": [
                "arn:aws:s3:::your-company-photos-raw-prod",
                "arn:aws:s3:::your-company-photos-processed-prod"
            ]
        },
        {
            "Sid": "AllowS3ObjectAccess",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:GetObjectVersion",
                "s3:PutObjectAcl"
            ],
            "Resource": [
                "arn:aws:s3:::your-company-photos-raw-prod/*",
                "arn:aws:s3:::your-company-photos-processed-prod/*"
            ]
        },
        {
            "Sid": "AllowPresignedUrlGeneration",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:PutObjectAcl"
            ],
            "Resource": [
                "arn:aws:s3:::your-company-photos-raw-prod/*"
            ]
        }
    ]
}
```

**Create and attach the policy**:
```bash
# Create policy
aws iam create-policy \
    --policy-name PhotoApiS3Policy \
    --policy-document file://photo-api-s3-policy.json

# Attach policy to role
aws iam attach-role-policy \
    --role-name PhotoApiEC2Role \
    --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/PhotoApiS3Policy
```

### 3. Create Instance Profile

```bash
# Create instance profile
aws iam create-instance-profile --instance-profile-name PhotoApiInstanceProfile

# Add role to instance profile
aws iam add-role-to-instance-profile \
    --instance-profile-name PhotoApiInstanceProfile \
    --role-name PhotoApiEC2Role
```

---

## 🖥️ EC2 Infrastructure

### 1. Security Group

**Create security group**:
```bash
aws ec2 create-security-group \
    --group-name photo-api-sg \
    --description "Security group for Photo API" \
    --vpc-id vpc-YOUR_VPC_ID
```

**Add inbound rules**:
```bash
# SSH access (limit to your IP)
aws ec2 authorize-security-group-ingress \
    --group-id sg-YOUR_SG_ID \
    --protocol tcp \
    --port 22 \
    --cidr YOUR_IP_ADDRESS/32

# HTTP API access (port 8080)
aws ec2 authorize-security-group-ingress \
    --group-id sg-YOUR_SG_ID \
    --protocol tcp \
    --port 8080 \
    --cidr 0.0.0.0/0

# HTTPS (if using SSL termination)
aws ec2 authorize-security-group-ingress \
    --group-id sg-YOUR_SG_ID \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0
```

### 2. Launch EC2 Instance

**Recommended instance type**: `t3.small` or `t3.medium`
- **t3.small**: 2 vCPU, 2 GiB RAM (~$15/month)
- **t3.medium**: 2 vCPU, 4 GiB RAM (~$30/month)

**Launch instance**:
```bash
aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316 \
    --count 1 \
    --instance-type t3.small \
    --key-name your-key-pair \
    --security-group-ids sg-YOUR_SG_ID \
    --subnet-id subnet-YOUR_SUBNET_ID \
    --iam-instance-profile Name=PhotoApiInstanceProfile \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=photo-api-server}]'
```

### 3. Elastic IP (Optional but Recommended)

**Allocate and associate**:
```bash
# Allocate Elastic IP
aws ec2 allocate-address --domain vpc

# Associate with instance
aws ec2 associate-address \
    --instance-id i-YOUR_INSTANCE_ID \
    --allocation-id eipalloc-YOUR_ALLOCATION_ID
```

---

## 🗄️ PostgreSQL Database Setup

### Option 1: PostgreSQL on EC2 (Simple, Lower Cost)

**Install PostgreSQL on your EC2 instance:**
```bash
# Update system
sudo apt update

# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**Configure PostgreSQL:**
```bash
# Switch to postgres user
sudo -u postgres psql

-- Create database and user
CREATE DATABASE photo_db_prod;
CREATE USER photo_user WITH PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE photo_db_prod TO photo_user;

-- Exit PostgreSQL
\q
```

**Configure PostgreSQL for connections:**
```bash
# Edit PostgreSQL config
sudo nano /etc/postgresql/14/main/postgresql.conf

# Add/modify these lines:
listen_addresses = 'localhost'

# Edit authentication config
sudo nano /etc/postgresql/14/main/pg_hba.conf

# Add this line for local connections:
local   photo_db_prod   photo_user                  md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Option 2: Amazon RDS PostgreSQL (Managed, Higher Cost)

**Create RDS instance:**
```bash
aws rds create-db-instance \
    --db-instance-identifier photo-api-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 15.4 \
    --master-username photo_user \
    --master-user-password YOUR_SECURE_PASSWORD \
    --allocated-storage 20 \
    --storage-type gp2 \
    --vpc-security-group-ids sg-YOUR_DB_SECURITY_GROUP \
    --db-subnet-group-name your-db-subnet-group \
    --backup-retention-period 7 \
    --storage-encrypted
```

**RDS Security Group:**
```bash
# Create security group for RDS
aws ec2 create-security-group \
    --group-name photo-api-db-sg \
    --description "Security group for Photo API database"

# Allow PostgreSQL access from EC2 security group
aws ec2 authorize-security-group-ingress \
    --group-id sg-YOUR_DB_SG_ID \
    --protocol tcp \
    --port 5432 \
    --source-group sg-YOUR_EC2_SG_ID
```

### Database Schema

The application automatically creates these tables on startup:

```sql
CREATE TABLE job_logs (
    id VARCHAR PRIMARY KEY,
    job_id VARCHAR NOT NULL UNIQUE,
    job_type VARCHAR NOT NULL,
    filename VARCHAR,
    s3_key VARCHAR,
    source_url VARCHAR,
    content_type VARCHAR,
    job_metadata TEXT,
    temporal_workflow_id VARCHAR NOT NULL,
    temporal_task_queue VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR NOT NULL DEFAULT 'submitted',
    error_message TEXT
);

CREATE INDEX idx_job_logs_job_id ON job_logs(job_id);
CREATE INDEX idx_job_logs_status ON job_logs(status);
CREATE INDEX idx_job_logs_created_at ON job_logs(created_at);
```

### Database Maintenance

**Backup script** (save as `/home/ubuntu/backup-db.sh`):
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h localhost -U photo_user photo_db_prod > /home/ubuntu/backups/photo_db_$DATE.sql
find /home/ubuntu/backups -name "photo_db_*.sql" -mtime +7 -delete
```

**Schedule backups:**
```bash
# Create backup directory
mkdir -p /home/ubuntu/backups

# Add to crontab
crontab -e

# Add this line for daily backups at 2 AM
0 2 * * * /home/ubuntu/backup-db.sh
```

---

## 🔄 Temporal Setup

### Option 1: Temporal Cloud (Recommended)

1. **Sign up** at [cloud.temporal.io](https://cloud.temporal.io)
2. **Create namespace**: `photo-processing-prod`
3. **Get connection details**:
   - Namespace: `photo-processing-prod.YOUR_ACCOUNT_ID`
   - Address: `photo-processing-prod.YOUR_ACCOUNT_ID.tmprl.cloud:7233`
4. **Download certificates** for mTLS authentication

**Environment variables for Temporal Cloud**:
```bash
TEMPORAL_TARGET=photo-processing-prod.YOUR_ACCOUNT_ID.tmprl.cloud:7233
TEMPORAL_NAMESPACE=photo-processing-prod.YOUR_ACCOUNT_ID
TEMPORAL_TASK_QUEUE=image-tasks
# Add certificate paths if using mTLS
```

### Option 2: Self-Hosted Temporal

**Docker Compose setup** on EC2:
```yaml
# temporal-docker-compose.yml
version: '3.8'
services:
  temporal:
    image: temporalio/auto-setup:latest
    ports:
      - "7233:7233"
    environment:
      - DB=postgresql
      - DB_PORT=5432
      - POSTGRES_USER=temporal
      - POSTGRES_PWD=temporal
      - POSTGRES_SEEDS=postgresql
    depends_on:
      - postgresql

  postgresql:
    image: postgres:13
    environment:
      POSTGRES_PASSWORD: temporal
      POSTGRES_USER: temporal
      POSTGRES_DB: temporal
    volumes:
      - temporal_postgresql:/var/lib/postgresql/data

  temporal-web:
    image: temporalio/web:latest
    ports:
      - "8088:8088"
    environment:
      - TEMPORAL_GRPC_ENDPOINT=temporal:7233

volumes:
  temporal_postgresql:
```

---

## 🚀 Deployment Steps

### 1. **Prepare Infrastructure**
```bash
# 1. Create S3 buckets
aws s3 mb s3://your-company-photos-raw-prod --region us-west-2
aws s3 mb s3://your-company-photos-processed-prod --region us-west-2

# 2. Create IAM role and policies (see above)

# 3. Launch EC2 instance with proper security group

# 4. Set up Temporal (Cloud or self-hosted)
```

### 2. **Configure EC2 Instance**
```bash
# SSH into instance
ssh -i your-key.pem ubuntu@YOUR_ELASTIC_IP

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker ubuntu

# Install Python 3.11+
sudo apt install -y python3.11 python3.11-pip python3.11-venv
```

### 3. **Deploy Application**
```bash
# Clone repository
git clone https://github.com/your-username/photo-api.git
cd photo-api

# Create environment file
cp .env.production .env
# Edit .env with actual values

# Build and run with Docker
docker build -t photo-api .
docker run -d \
    --name photo-api \
    --restart unless-stopped \
    -p 8080:8080 \
    --env-file .env \
    photo-api
```

### 4. **Verify Deployment**
```bash
# Test health endpoint
curl http://YOUR_ELASTIC_IP:8080/healthz

# Test with API key
curl -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"content_type":"image/jpeg","max_bytes":5000000}' \
     http://YOUR_ELASTIC_IP:8080/uploads/init
```

---

## 💰 Cost Estimate

### Monthly Costs (us-west-2):
- **EC2 t3.small**: ~$15/month
- **PostgreSQL on EC2**: $0 (included with EC2)
- **RDS db.t3.micro** (optional): ~$12/month
- **S3 storage**: ~$0.023/GB/month
- **S3 requests**: ~$0.0004 per 1,000 requests
- **Data transfer**: First 1GB free, then ~$0.09/GB
- **Temporal Cloud**: ~$25/month (basic plan)

**Total estimated cost**:
- **With PostgreSQL on EC2**: ~$40-50/month
- **With RDS PostgreSQL**: ~$52-62/month

---

## 🔒 Security Checklist

- ✅ **S3 buckets** have public access blocked
- ✅ **IAM role** uses least-privilege permissions
- ✅ **Security group** restricts access to necessary ports
- ✅ **API key authentication** enabled
- ✅ **HTTPS** configured (add SSL certificate)
- ✅ **Regular security updates** on EC2 instance
- ✅ **Environment variables** not in source code
- ✅ **SSH key** properly secured

---

## 📝 Environment Variables

**Production `.env` file**:
```bash
# AWS Configuration
AWS_REGION=us-west-2
S3_BUCKET_RAW=your-company-photos-raw-prod
S3_BUCKET_PROCESSED=your-company-photos-processed-prod

# Database Configuration
DATABASE_URL=postgresql+asyncpg://photo_user:secure_password@localhost:5432/photo_db_prod

# Temporal Configuration
TEMPORAL_TARGET=your-temporal-endpoint:7233
TEMPORAL_NAMESPACE=photo-processing-prod
TEMPORAL_TASK_QUEUE=image-tasks

# API Configuration
API_KEY=YOUR_SECURE_GENERATED_API_KEY
CORS_ORIGINS=http://localhost:3000,https://your-domain.com
DEBUG=false
LOG_LEVEL=INFO

# Upload Configuration
PRESIGN_EXPIRES_SECONDS=300
MAX_UPLOAD_SIZE=25000000
```

---

## 🔧 Maintenance

### Regular Tasks:
- **Monitor disk usage** on EC2 instance
- **Review S3 costs** and storage usage
- **Update Docker image** with latest security patches
- **Backup configuration** and environment files
- **Monitor Temporal workflows** for failures
- **Review CloudWatch logs** for errors
- **Backup PostgreSQL database** (automatic with cron job)
- **Monitor job logs table** for failed jobs
- **Clean up old job logs** (optional, for storage management)

### Scaling Up (If Needed):
- Upgrade EC2 instance type
- Add Application Load Balancer
- Enable auto-scaling
- Add CloudFront for global distribution
- Implement proper logging with CloudWatch

This infrastructure setup provides a **simple, secure, and cost-effective** foundation for running your photo API in production!
@echo off
set PROJECT_NAME=缺陷管理系统
set MYSQL_SERVER=localhost
set MYSQL_PORT=3306
set MYSQL_DB=qa_assistant
set MYSQL_USER=root
set MYSQL_PASSWORD=123456
set MONGODB_URL=mongodb://localhost:27017
set MONGODB_DB_NAME=test_platform
set SECRET_KEY=changethis
set ACCESS_TOKEN_EXPIRE_MINUTES=11520
set FIRST_SUPERUSER=admin@example.com
set FIRST_SUPERUSER_PASSWORD=changethis
set SMTP_HOST=smtp.qq.com
set SMTP_PORT=465
set SMTP_USER=your-email@qq.com
set SMTP_PASSWORD=your-password
set EMAILS_FROM_EMAIL=your-email@qq.com
set ENVIRONMENT=local
set FRONTEND_HOST=http://localhost:5173
set APIFOX_ACCESS_TOKEN=afxp_8a53312G2fCZen2C4pyPor0MGME8wT9eWe7B
set APIFOX_PROJECT_ID=7822130
set LOG_FILE=logs\app.log
set LOG_LEVEL=INFO

.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

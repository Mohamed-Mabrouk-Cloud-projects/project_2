# This code put on user data of our EC2 during we create it 
# and you should create RDS and S3 in the beginning because we use them in 
# our User Data like DB_endpoint of Data Base  and DB_password and DB_user and other 
# as we I show in this file 

#!/bin/bash
set -euxo pipefail

REPO_DIR="/opt/job-app-repo"
APP_DIR="/opt/job-app-repo/employee-job-application-cloud-system"

AWS_REGION="us-east-1"
S3_BUCKET="rds-bucket-19"

DB_HOST="database-1.caxcaqcocc4x.us-east-1.rds.amazonaws.com"
DB_NAME="job_applications"
DB_USER="admin"
DB_PASSWORD="admin1234"

GITHUB_REPO="https://github.com/Mohamed-Mabrouk-Cloud-projects/project_2"

# Install required packages
apt-get update -y
apt-get install -y python3 python3-venv python3-pip mysql-client git

# Clone project
git clone --depth 1 --branch main "$GITHUB_REPO" "$REPO_DIR"

# Create virtual environment
python3 -m venv "$APP_DIR/venv"

# Install requirements
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/app/requirements.txt"

# Set environment variables
export DB_HOST="$DB_HOST"
export DB_PORT="3306"
export DB_NAME="$DB_NAME"
export DB_USER="$DB_USER"
export DB_PASSWORD="$DB_PASSWORD"
export S3_BUCKET="$S3_BUCKET"
export AWS_REGION="$AWS_REGION"

# Create database and tables in RDS
mysql \
    --host="$DB_HOST" \
    --user="$DB_USER" \
    --password="$DB_PASSWORD" \
    --protocol=tcp < "$APP_DIR/database/schema.sql"

# Run Flask application
cd "$APP_DIR/app"
"$APP_DIR/venv/bin/python" app.py

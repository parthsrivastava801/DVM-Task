# DVM Bus Manager - PostgreSQL Migration & Deployment Guide

This guide provides step-by-step instructions for migrating DVM Bus Manager from SQLite to PostgreSQL and deploying to a production environment.

## Prerequisites

- PostgreSQL server installed and running
- Access to a production server with Python 3.9+ installed
- Administrative privileges to create databases and users in PostgreSQL

## Step 1: Set Up PostgreSQL Database

1. Install PostgreSQL if not already installed:
   ```bash
   # For Ubuntu/Debian
   sudo apt update
   sudo apt install postgresql postgresql-contrib
   
   # For RHEL/CentOS/Fedora
   sudo dnf install postgresql postgresql-server
   sudo postgresql-setup --initdb
   sudo systemctl start postgresql
   ```

2. Create a PostgreSQL database and user:
   ```bash
   sudo -u postgres psql
   ```

   In the PostgreSQL prompt:
   ```sql
   CREATE DATABASE busbliss;
   CREATE USER busblissuser WITH PASSWORD 'your_secure_password';
   ALTER ROLE busblissuser SET client_encoding TO 'utf8';
   ALTER ROLE busblissuser SET default_transaction_isolation TO 'read committed';
   ALTER ROLE busblissuser SET timezone TO 'UTC';
   GRANT ALL PRIVILEGES ON DATABASE busbliss TO busblissuser;
   \q
   ```

## Step 2: Configure Environment Variables

1. Create a `.env` file based on the example:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file with your production settings:
   ```
   DB_NAME=busbliss
   DB_USER=busblissuser
   DB_PASSWORD=your_secure_password
   DB_HOST=localhost
   DB_PORT=5432
   
   SECRET_KEY=your_secure_django_secret_key
   DEBUG=False
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   
   # Email settings
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-app-password
   DEFAULT_FROM_EMAIL=DVM Bus Manager <noreply@yourdomain.com>
   ```

## Step 3: Install Production Requirements

```bash
pip install -r requirements.production.txt
```

## Step 4: Migrate from SQLite to PostgreSQL

1. Make sure your `.env` file is configured correctly with PostgreSQL credentials

2. Run the migration script:
   ```bash
   python migrate_to_postgres.py
   ```

   This script will:
   - Extract data from SQLite
   - Create the schema in PostgreSQL
   - Import all data to PostgreSQL

3. Verify the migration:
   ```bash
   python manage.py shell -c "from django.db import connection; print(connection.vendor)"
   ```
   Should output: `postgresql`

## Step 5: Configure Production Web Server

1. Install and configure Gunicorn:

   ```bash
   pip install gunicorn
   ```

2. Create a Gunicorn service file (for systemd):
   
   ```bash
   sudo nano /etc/systemd/system/busbliss.service
   ```

   Add the following content:
   ```
   [Unit]
   Description=DVM Bus Manager Django Application
   After=network.target postgresql.service
   
   [Service]
   User=your_user
   Group=your_group
   WorkingDirectory=/path/to/Bus-Bliss
   ExecStart=/path/to/Bus-Bliss/venv/bin/gunicorn --workers 3 --bind unix:/path/to/Bus-Bliss/busbliss.sock Bus_Booking.wsgi:application
   Restart=on-failure
   
   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start the service:
   ```bash
   sudo systemctl enable busbliss
   sudo systemctl start busbliss
   ```

4. Configure Nginx (recommended):
   
   ```bash
   sudo nano /etc/nginx/sites-available/busbliss
   ```

   Add the following configuration:
   ```
   server {
       listen 80;
       server_name yourdomain.com www.yourdomain.com;
   
       location = /favicon.ico { access_log off; log_not_found off; }
       
       location /static/ {
           root /path/to/Bus-Bliss;
       }
   
       location / {
           include proxy_params;
           proxy_pass http://unix:/path/to/Bus-Bliss/busbliss.sock;
       }
   }
   ```

5. Enable the site and restart Nginx:
   ```bash
   sudo ln -s /etc/nginx/sites-available/busbliss /etc/nginx/sites-enabled/
   sudo systemctl restart nginx
   ```

## Step 6: Collect Static Files

```bash
python manage.py collectstatic
```

## Step 7: Configure HTTPS (recommended)

1. Install Certbot:
   ```bash
   sudo apt install certbot python3-certbot-nginx
   ```

2. Obtain and configure SSL certificate:
   ```bash
   sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
   ```

## Troubleshooting

- **Database Connection Issues**: Verify PostgreSQL is running and credentials are correct
  ```bash
  sudo systemctl status postgresql
  ```

- **Permission Denied**: Check file permissions and ownership
  ```bash
  sudo chown -R your_user:your_group /path/to/Bus-Bliss
  ```

- **Migration Errors**: Check the data_migration.log file for details

- **Server Errors**: Check Gunicorn and Nginx logs
  ```bash
  sudo journalctl -u busbliss.service
  sudo tail -f /var/log/nginx/error.log
  ```

## Backup and Restore

- **Backup PostgreSQL Database**:
  ```bash
  pg_dump -U busblissuser -d busbliss > busbliss_backup.sql
  ```

- **Restore PostgreSQL Database**:
  ```bash
  psql -U busblissuser -d busbliss < busbliss_backup.sql
  ```

## Additional Security Recommendations

1. **Configure Firewall**: Restrict access to only necessary ports (80, 443)
   ```bash
   sudo ufw allow 'Nginx Full'
   sudo ufw enable
   ```

2. **Regular Backups**: Set up automated backups of the database
   ```bash
   # Add to crontab
   0 2 * * * pg_dump -U busblissuser -d busbliss > /path/to/backups/busbliss_$(date +\%Y\%m\%d).sql
   ```

3. **Security Updates**: Keep the system updated
   ```bash
   sudo apt update && sudo apt upgrade
   ```

4. **Database Hardening**: Configure PostgreSQL for security
   ```bash
   # Edit pg_hba.conf and postgresql.conf
   
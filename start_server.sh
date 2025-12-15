#!/bin/bash
# 线上环境 IP:10.19.1.14 port:10272

cd /data/BankTables/
source source backend/venv/bin/activate
nohup python3 backend_run.py  > logs/app.log 2>&1 &


cd frontend
nohup npm run serve &


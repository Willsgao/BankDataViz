#!/bin/bash

cd /data/BankTables/
source backend/venv/bin/activate

sudo chmod -R 777 data

nohup python3 backend_run.py  > logs/app.log 2>&1 &


cd frontend
nohup npm run serve &


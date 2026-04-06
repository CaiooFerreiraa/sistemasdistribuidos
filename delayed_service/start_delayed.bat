@echo off
if "%UPSTREAM_BASE_URL%"=="" (
  echo Defina UPSTREAM_BASE_URL antes de executar.
  echo Exemplo: set UPSTREAM_BASE_URL=http://192.168.1.50:8000
  exit /b 1
)

set REPLICA_POLL_INTERVAL_SECONDS=%REPLICA_POLL_INTERVAL_SECONDS%
if "%REPLICA_POLL_INTERVAL_SECONDS%"=="" set REPLICA_POLL_INTERVAL_SECONDS=60

set RELEASE_DELAY_SECONDS=%RELEASE_DELAY_SECONDS%
if "%RELEASE_DELAY_SECONDS%"=="" set RELEASE_DELAY_SECONDS=60

set RETRY_AFTER_ERROR_SECONDS=%RETRY_AFTER_ERROR_SECONDS%
if "%RETRY_AFTER_ERROR_SECONDS%"=="" set RETRY_AFTER_ERROR_SECONDS=5

if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001
) else (
  python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
)

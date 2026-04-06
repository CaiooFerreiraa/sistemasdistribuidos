@echo off
set CITY_NAME=%CITY_NAME%
if "%CITY_NAME%"=="" set CITY_NAME=Salvador

set COUNTRY_CODE=%COUNTRY_CODE%
if "%COUNTRY_CODE%"=="" set COUNTRY_CODE=BR

set POLL_INTERVAL_SECONDS=%POLL_INTERVAL_SECONDS%
if "%POLL_INTERVAL_SECONDS%"=="" set POLL_INTERVAL_SECONDS=15

if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
) else (
  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
)

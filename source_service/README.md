# Servidor 1: Origem da Temperatura

Instale esta pasta na máquina 1.

## Instalação

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Execução

```cmd
start_source.bat
```

## Configuração opcional

```cmd
set CITY_NAME=Salvador
set COUNTRY_CODE=BR
set POLL_INTERVAL_SECONDS=15
start_source.bat
```

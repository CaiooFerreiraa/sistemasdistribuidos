# Servidor 2: Replica com Atraso de 1 Minuto

Instale esta pasta na máquina 2.

## Instalação

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Execução

```cmd
set UPSTREAM_BASE_URL=http://192.168.1.50:8000
start_delayed.bat
```

## Endpoints

- `GET /health`
- `GET /temperature/latest`
- `GET /payload`
- `GET /temperature/pipeline`
- `GET /docs`

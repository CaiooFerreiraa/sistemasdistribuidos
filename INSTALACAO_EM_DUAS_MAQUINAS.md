# Instalacao em Duas Maquinas

## Maquina 1: servidor de origem

Copie a pasta `source_service` para a máquina 1.

Instale e rode:

```powershell
cd source_service
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
start_source.bat
```

Esse servidor ficará disponível na porta `8000`.

## Maquina 2: servidor replica

Copie a pasta `delayed_service` para a máquina 2.

Instale e rode:

```powershell
cd delayed_service
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
set UPSTREAM_BASE_URL=http://IP_DA_MAQUINA_1:8000
start_delayed.bat
```

Esse servidor ficará disponível na porta `8001`.

## Como acessar de outra maquina

### Na mesma rede local

1. Descubra o IP da máquina 1 com `ipconfig`.
2. Descubra o IP da máquina 2 com `ipconfig`.
3. Libere as portas `8000` e `8001` no firewall do Windows, se necessário.
4. Acesse:

- origem: `http://IP_DA_MAQUINA_1:8000/temperature/latest`
- réplica: `http://IP_DA_MAQUINA_2:8001/payload`

### Em qualquer rede pela internet

Você precisa expor cada máquina com uma destas opções:

1. VPS ou nuvem.
2. Port forwarding no roteador com IP público ou domínio.
3. Túnel como ngrok ou Cloudflare Tunnel.

Sem IP público, túnel ou redirecionamento de porta, outra rede não consegue acessar diretamente.

## Exemplo real

Se a máquina 1 estiver no IP `192.168.1.50` e a máquina 2 no IP `192.168.1.60`:

- máquina 1: sobe `source_service` na porta `8000`
- máquina 2: configura `UPSTREAM_BASE_URL=http://192.168.1.50:8000`
- clients: consomem `http://192.168.1.60:8001/payload`

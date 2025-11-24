# ExpressRoute Monitoring for Zabbix

Zabbix monitoring system deployed with Docker Compose.

## Prerequisites

- Docker installed
- Docker Compose installed
- Available ports: 8081, 10050, 10051

## Installation

### 1. Start the containers

```bash
sudo docker compose up -d
```

This command downloads the necessary images (if it's the first time) and starts all services in the background.

### 2. Verify the status

```bash
sudo docker-compose ps
```

You should see 4 containers in "running" state:
- zabbix-mysql
- zabbix-server
- zabbix-web
- zabbix-agent

### 3. Wait for initialization

Wait 2-5 minutes for MySQL to initialize the database and Zabbix Server to create the necessary tables.

You can monitor the logs with:

```bash
sudo docker-compose logs -f zabbix-server
```

The server will be ready when you see the message: `server #0 started [main process]`

## Web Interface Access

### Access URL

```
http://localhost:8081
```

### Default credentials

- Username: `Admin`
- Password: `zabbix`

Note: The 'A' in Admin is uppercase.

## Configuration

### 4. Add a test Host (localhost)

In the web interface:

1. Go to **Data collection** → **Hosts**
2. Click **Create host**
3. Fill in the host configuration:
   - **Host name**: `local-test`
   - **Groups**: Select `Discovered hosts` or create a new group
   - **Interfaces**: Click **Add** → Select **Agent**
     - **IP address**: Leave empty or any value
     - **DNS name**: `zabbix-agent`
     - **Connect to**: Select **DNS** (not IP)
     - **Port**: `10050`
4. Go to the **Templates** tab
5. Click **Select** and add: `Linux by Zabbix agent`
6. Click **Add** (at the bottom of the page)

The Zabbix Agent container will start sending data automatically.

> **Note**: Use DNS name instead of IP address because containers communicate through Docker's internal network using service names defined in docker-compose.yml.

### 5. Add ExpressRoute monitoring script

Create the scripts directory (if it doesn't exist):

```bash
mkdir -p scripts
chmod 755 scripts
```

Save your script inside:

```bash
scripts/expressroute_rpo.py
```

Make it executable:

```bash
chmod +x scripts/expressroute_rpo.py
```

This script will be automatically available inside the Zabbix server container at:

```
/usr/lib/zabbix/externalscripts/expressroute_rpo.py
```

### 6. Verify script availability

Check that the script is mounted correctly:

```bash
docker exec zabbix-server ls -la /usr/lib/zabbix/externalscripts/
```

Test the script execution:

```bash
docker exec zabbix-server python3 /usr/lib/zabbix/externalscripts/expressroute_rpo.py test_circuit
```

You should see a JSON response with simulated data.

## Creating Monitoring Items

### 7. Create a Master Item to execute the script

On your `local-test` host:

1. Go to **Data collection** → **Hosts**
2. Select `local-test`
3. Click on **Items** → **Create item**
4. Configure the master item:
   - **Name**: `ExpressRoute RAW`
   - **Type**: `External check`
   - **Key**: `expressroute_rpo.py["vm-name-de-prueba"]`
   - **Type of information**: `Text`
   - **Update interval**: `60s`
5. Click **Add**

This item executes your script and stores the complete JSON response.

> **Note**: The key format for external checks in Zabbix is `script_name[parameters]`. The script must be executable and located in `/usr/lib/zabbix/externalscripts/`.

### 8. Create Dependent Items (parsing JSON data)

Now create dependent items to extract specific values from the JSON response:

#### Example: RPO Last Value

1. On the same host, click **Items** → **Create item**
2. Configure:
   - **Name**: `RPO last`
   - **Type**: `Dependent item`
   - **Master item**: Select `ExpressRoute RAW`
   - **Key**: `expressroute.rpo["vm-name-de-prueba"]`
   - **Type of information**: `Numeric (unsigned)`
3. Go to the **Preprocessing** tab:
   - Click **Add**
   - **Name**: `JSONPath`
   - **Parameters**: `$.data[0].RPO`
4. Click **Add**

This item extracts the RPO value from the JSON using JSONPath.

#### Example: Hostname/Circuit Name

1. Create another dependent item:
   - **Name**: `ExpressRoute Circuit Name`
   - **Type**: `Dependent item`
   - **Master item**: `ExpressRoute RAW`
   - **Key**: `expressroute.hostname["vm-name-de-prueba"]`
   - **Type of information**: `Text`
2. **Preprocessing**:
   - **JSONPath**: `$.data[0].HOSTNAME`
3. Click **Add**

### 9. Create Triggers (Alerts)

Create triggers to generate alerts based on thresholds:

#### Example: Alert if RPO exceeds 300 seconds

1. Go to **Data collection** → **Hosts**
2. Select `local-test` → **Triggers** → **Create trigger**
3. Configure:
   - **Name**: `ExpressRoute RPO is too high`
   - **Severity**: `Warning` or `High`
   - **Expression**: Click **Add**
     - Item: Select `RPO last`
     - Function: `last()`
     - Operator: `>`
     - Value: `300`
   
   Or manually enter the expression:
   ```
   last(/local-test/expressroute_rpo.py["vm-name-de-prueba"].rpo)>300
   ```

4. **Description** (optional):
   ```
   ExpressRoute RPO value is {ITEM.LASTVALUE}, exceeding the threshold of 300 seconds.
   ```
5. Click **Add**

The trigger will fire when the RPO value exceeds 300 seconds.

## Troubleshooting

### Check container logs

```bash
# Zabbix Server logs
sudo docker-compose logs -f zabbix-server

# All services
sudo docker-compose logs -f
```

### Restart services

```bash
sudo docker-compose restart
```

### Complete reset

```bash
sudo docker-compose down -v
sudo docker-compose up -d
```

## Notes

- The monitoring script runs in **simulated mode** by default (`SIMULATED_MODE = True`)
- To use real Azure ExpressRoute monitoring, modify the script configuration and set `SIMULATED_MODE = False`
- Ensure the Zabbix server has network access to Azure IMDS endpoint when using real mode
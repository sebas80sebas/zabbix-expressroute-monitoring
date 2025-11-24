# ExpressRoute Monitoring for Zabbix

Zabbix monitoring system installed locally on Ubuntu 24.04 following the official Zabbix documentation.

## Prerequisites

- Ubuntu 24.04 LTS
- MySQL Server installed and running
- Apache2 installed and running
- Available ports: 80 (Apache), 10050 (Zabbix Agent), 10051 (Zabbix Server)

## Installation

### 1. Install Zabbix 7.4

Follow the official Zabbix installation guide for Ubuntu 24.04:

```bash
# Download and install Zabbix repository
wget https://repo.zabbix.com/zabbix/7.4/release/ubuntu/pool/main/z/zabbix-release/zabbix-release_latest_7.4+ubuntu24.04_all.deb
dpkg -i zabbix-release_latest_7.4+ubuntu24.04_all.deb
apt update

# Install Zabbix components
apt install zabbix-server-mysql zabbix-frontend-php zabbix-apache-conf zabbix-sql-scripts zabbix-agent
```

### 2. Configure MySQL database

```bash
# Access MySQL
mysql -uroot -p

# Create database and user
CREATE DATABASE zabbix CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
CREATE USER 'zabbix'@'localhost' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON zabbix.* TO 'zabbix'@'localhost';
SET GLOBAL log_bin_trust_function_creators = 1;
QUIT;

# Import initial schema
zcat /usr/share/zabbix-sql-scripts/mysql/server.sql.gz | mysql --default-character-set=utf8mb4 -uzabbix -ppassword zabbix

# Disable log_bin_trust_function_creators
mysql -uroot -p -e "SET GLOBAL log_bin_trust_function_creators = 0;"
```

### 3. Configure Zabbix Server

Edit the configuration file:

```bash
nano /etc/zabbix/zabbix_server.conf
```

Find and set the database password:

```
DBPassword=password
```

### 4. Start and enable services

```bash
systemctl restart zabbix-server zabbix-agent apache2
systemctl enable zabbix-server zabbix-agent apache2
```

### 5. Verify installation

Check service status:

```bash
systemctl status zabbix-server zabbix-agent apache2
```

Check logs:

```bash
tail -f /var/log/zabbix/zabbix_server.log
```

## Web Interface Access

### Access URL

```
http://localhost/zabbix
```

or

```
http://your-server-ip/zabbix
```

### Initial Setup Wizard

Complete the web installation wizard:
1. Check pre-requisites (all should be green)
2. Configure database connection:
   - Database type: MySQL
   - Database host: localhost
   - Database port: 0 (default)
   - Database name: zabbix
   - User: zabbix
   - Password: password
3. Set Zabbix server details (leave defaults)
4. Review settings summary
5. Finish installation

### Default credentials

- Username: `Admin`
- Password: `zabbix`

**Important**: Change the Admin password immediately after first login.

## Configuration

### 6. Add a test Host (localhost)

In the web interface:

1. Go to **Data collection** → **Hosts**
2. Click **Create host**
3. Fill in the host configuration:
   - **Host name**: `local-test`
   - **Groups**: Select `Linux servers` or create a new group
   - **Interfaces**: Click **Add** → Select **Agent**
     - **IP address**: `127.0.0.1`
     - **DNS name**: `localhost`
     - **Connect to**: Select **IP**
     - **Port**: `10050`
4. Go to the **Templates** tab
5. Click **Select** and add: `Linux by Zabbix agent`
6. Click **Add** (at the bottom of the page)

The local Zabbix Agent will start sending data automatically.

### 7. Add ExpressRoute monitoring script

Create the external scripts directory (if it doesn't exist):

```bash
mkdir -p /usr/lib/zabbix/externalscripts
chmod 755 /usr/lib/zabbix/externalscripts
```

Copy your script:

```bash
sudo cp expressroute_rpo.py /usr/lib/zabbix/externalscripts/
sudo chmod +x /usr/lib/zabbix/externalscripts/expressroute_rpo.py
```

Set proper ownership:

```bash
sudo chown zabbix:zabbix /usr/lib/zabbix/externalscripts/expressroute_rpo.py
```

### 8. Verify script availability

Test the script execution:

```bash
sudo -u zabbix python3 /usr/lib/zabbix/externalscripts/expressroute_rpo.py test_circuit
```

You should see a JSON response with simulated data.

## Creating Monitoring Items

### 9. Create a Master Item to execute the script

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

### 10. Create Dependent Items (parsing JSON data)

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

### 11. Create Additional Dependent Items

Create these additional items to monitor more metrics:

#### 11.1 Circuit State

- **Name**: `ExpressRoute Circuit State`
- **Type**: `Dependent item`
- **Master item**: `ExpressRoute RAW`
- **Key**: `expressroute.circuit.state["vm-name-de-prueba"]`
- **Type of information**: `Character`
- **Preprocessing**: JSONPath → `$.data[0].CIRCUIT_STATE`

#### 11.2 BGP State

- **Name**: `ExpressRoute BGP State`
- **Type**: `Dependent item`
- **Master item**: `ExpressRoute RAW`
- **Key**: `expressroute.bgp.state["vm-name-de-prueba"]`
- **Type of information**: `Character`
- **Preprocessing**: JSONPath → `$.data[0].BGP_STATE`

#### 11.3 ARP Availability

- **Name**: `ExpressRoute ARP Availability`
- **Type**: `Dependent item`
- **Master item**: `ExpressRoute RAW`
- **Key**: `expressroute.arp.availability["vm-name-de-prueba"]`
- **Type of information**: `Numeric (float)`
- **Units**: `%`
- **Preprocessing**: JSONPath → `$.data[0].ARP_AVAILABILITY`

#### 11.4 BGP Availability

- **Name**: `ExpressRoute BGP Availability`
- **Type**: `Dependent item`
- **Master item**: `ExpressRoute RAW`
- **Key**: `expressroute.bgp.availability["vm-name-de-prueba"]`
- **Type of information**: `Numeric (float)`
- **Units**: `%`
- **Preprocessing**: JSONPath → `$.data[0].BGP_AVAILABILITY`

#### 11.5 Inbound Bandwidth

- **Name**: `ExpressRoute Bandwidth In`
- **Type**: `Dependent item`
- **Master item**: `ExpressRoute RAW`
- **Key**: `expressroute.bandwidth.in["vm-name-de-prueba"]`
- **Type of information**: `Numeric (float)`
- **Units**: `Mbps`
- **Preprocessing**: JSONPath → `$.data[0].BANDWIDTH_IN_MBPS`

#### 11.6 Outbound Bandwidth

- **Name**: `ExpressRoute Bandwidth Out`
- **Type**: `Dependent item`
- **Master item**: `ExpressRoute RAW`
- **Key**: `expressroute.bandwidth.out["vm-name-de-prueba"]`
- **Type of information**: `Numeric (float)`
- **Units**: `Mbps`
- **Preprocessing**: JSONPath → `$.data[0].BANDWIDTH_OUT_MBPS`

#### 11.7 Latency

- **Name**: `ExpressRoute Latency`
- **Type**: `Dependent item`
- **Master item**: `ExpressRoute RAW`
- **Key**: `expressroute.latency["vm-name-de-prueba"]`
- **Type of information**: `Numeric (float)`
- **Units**: `ms`
- **Preprocessing**: JSONPath → `$.data[0].LATENCY_MS`

#### 11.8 Overall Status

- **Name**: `ExpressRoute Overall Status`
- **Type**: `Dependent item`
- **Master item**: `ExpressRoute RAW`
- **Key**: `expressroute.status["vm-name-de-prueba"]`
- **Type of information**: `Character`
- **Preprocessing**: JSONPath → `$.data[0].STATUS`

#### 11.9 Last Check Timestamp

- **Name**: `ExpressRoute Last Check`
- **Type**: `Dependent item`
- **Master item**: `ExpressRoute RAW`
- **Key**: `expressroute.timestamp["vm-name-de-prueba"]`
- **Type of information**: `Numeric (unsigned)`
- **Units**: `unixtime`
- **Preprocessing**: JSONPath → `$.data[0].TIMESTAMP`

## Creating Triggers (Alerts)

Create triggers to generate alerts based on thresholds:

### 12. Advanced Triggers

#### 12.1 High RPO

- **Name**: `ExpressRoute RPO is too high on {HOST.NAME}`
- **Severity**: `High`
- **Expression**: `last(/local-test/expressroute.rpo["vm-name-de-prueba"])>300`
- **Recovery expression**: `last(/local-test/expressroute.rpo["vm-name-de-prueba"])<200`
- **Description**: `RPO value is {ITEM.LASTVALUE}s, exceeding threshold of 300s`

#### 12.2 Circuit Disabled

- **Name**: `ExpressRoute Circuit is not Enabled`
- **Severity**: `Disaster`
- **Expression**: `last(/local-test/expressroute.circuit.state["vm-name-de-prueba"])<>"Enabled"`
- **Description**: `Circuit state is {ITEM.LASTVALUE}, expected Enabled`

#### 12.3 BGP Disconnected

- **Name**: `ExpressRoute BGP Connection Lost`
- **Severity**: `High`
- **Expression**: `last(/local-test/expressroute.bgp.state["vm-name-de-prueba"])<>"Connected"`
- **Description**: `BGP state is {ITEM.LASTVALUE}`

#### 12.4 Low BGP Availability

- **Name**: `ExpressRoute BGP Availability below 95%`
- **Severity**: `Warning`
- **Expression**: `last(/local-test/expressroute.bgp.availability["vm-name-de-prueba"])<95`
- **Description**: `BGP availability is {ITEM.LASTVALUE}%, below 95% threshold`

#### 12.5 Low ARP Availability

- **Name**: `ExpressRoute ARP Availability below 95%`
- **Severity**: `Warning`
- **Expression**: `last(/local-test/expressroute.arp.availability["vm-name-de-prueba"])<95`
- **Description**: `ARP availability is {ITEM.LASTVALUE}%, below 95% threshold`

#### 12.6 High Latency

- **Name**: `ExpressRoute Latency is high`
- **Severity**: `Warning`
- **Expression**: `last(/local-test/expressroute.latency["vm-name-de-prueba"])>30`
- **Description**: `Latency is {ITEM.LASTVALUE}ms, exceeding 30ms threshold`

#### 12.7 High Bandwidth Utilization

- **Name**: `ExpressRoute Bandwidth utilization is high`
- **Severity**: `Warning`
- **Expression**: `last(/local-test/expressroute.bandwidth.in["vm-name-de-prueba"])>800`
- **Description**: `Incoming bandwidth is {ITEM.LASTVALUE}Mbps, exceeding 80% of capacity (1000 Mbps)`

## Testing Triggers

### Test Trigger with script

Edit the script to modify the RPO value:

```bash
sudo nano /usr/lib/zabbix/externalscripts/expressroute_rpo.py
```

Modify the RPO line to return a high value:

```
"RPO": 450
```

Save the file and test:

```bash
sudo -u zabbix python3 /usr/lib/zabbix/externalscripts/expressroute_rpo.py test_circuit
```

### Run Test Script

Copy and execute the test script to verify all monitoring components:

```bash
sudo cp test_expressroute.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/test_expressroute.sh
sudo /usr/local/bin/test_expressroute.sh
```

This script will validate the configuration and trigger all alerts for testing purposes.

### Verify the outputs in Zabbix

**Monitoring → Problems**: All active problems appear here. You will see "RPO too high" when RPO > 300.

**Monitoring → Latest data**: Filter by local-test. Click on the RPO last value to see the current value. If it is >300, the trigger should be active.

**Monitoring → Hosts**: Look at the Problems column. If the trigger is active, you will see a red number.

## Troubleshooting

### Check service status

```bash
systemctl status zabbix-server zabbix-agent apache2
```

### Check logs

```bash
# Zabbix Server logs
tail -f /var/log/zabbix/zabbix_server.log

# Apache logs
tail -f /var/log/apache2/error.log
tail -f /var/log/apache2/access.log
```

### Restart services

```bash
systemctl restart zabbix-server zabbix-agent apache2
```

### Test external script manually

```bash
sudo -u zabbix /usr/lib/zabbix/externalscripts/expressroute_rpo.py test_circuit
```

### Verify script permissions

```bash
ls -la /usr/lib/zabbix/externalscripts/expressroute_rpo.py
```

Should show:
```
-rwxr-xr-x 1 zabbix zabbix ... expressroute_rpo.py
```

## Configuration Files Location

- Zabbix Server config: `/etc/zabbix/zabbix_server.conf`
- Zabbix Agent config: `/etc/zabbix/zabbix_agent.conf`
- Apache Zabbix config: `/etc/apache2/conf-enabled/zabbix.conf`
- External scripts: `/usr/lib/zabbix/externalscripts/`
- Logs: `/var/log/zabbix/`

## Notes

- The monitoring script runs in **simulated mode** by default (`SIMULATED_MODE = True`)
- To use real Azure ExpressRoute monitoring, modify the script configuration and set `SIMULATED_MODE = False`
- Ensure the Zabbix server has network access to Azure IMDS endpoint when using real mode
- Default timezone for Zabbix web interface can be configured in **Administration** → **Users** → **Admin** → **User** tab
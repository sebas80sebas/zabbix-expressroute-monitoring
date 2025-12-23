# Azure ExpressRoute Monitoring Setup Guide

This guide explains how to set up monitoring for Azure ExpressRoute circuits using Zabbix with Managed Identity authentication.

## Overview

This setup allows a Zabbix proxy running on an Azure VM to monitor ExpressRoute circuits using Azure's Managed Identity for secure authentication, eliminating the need for storing credentials.

## Prerequisites

- Azure VM with Managed Identity enabled
- Zabbix server installed on the VM
- Python 3.8+ with `requests` module
- Azure CLI installed and configured
- Appropriate Azure subscription access

## Step 1: Configure Managed Identity

### 1.1 Verify Managed Identity

First, retrieve your VM's Managed Identity Principal ID:

```bash
VM_IDENTITY=$(az vm show -g <RESOURCE_GROUP> -n <VM_NAME> --query identity.principalId -o tsv)
echo $VM_IDENTITY
```

Expected output format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

### 1.2 Test Managed Identity Token

Verify the VM can obtain authentication tokens:

```bash
curl -H "Metadata:true" "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/"
```

## Step 2: Assign Azure Roles

### 2.1 Get Subscription ID

```bash
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
```

### 2.2 Assign Reader Role

Grant the Managed Identity read access to the ExpressRoute circuit:

```bash
az role assignment create \
  --assignee-object-id $VM_IDENTITY \
  --assignee-principal-type ServicePrincipal \
  --role "Reader" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/<RESOURCE_GROUP>/providers/Microsoft.Network/expressRouteCircuits/<CIRCUIT_NAME>"
```

### 2.3 Assign Monitoring Reader Role

Grant access to metrics data:

```bash
az role assignment create \
  --assignee-object-id $VM_IDENTITY \
  --assignee-principal-type ServicePrincipal \
  --role "Monitoring Reader" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/<RESOURCE_GROUP>/providers/Microsoft.Network/expressRouteCircuits/<CIRCUIT_NAME>"
```

### 2.4 Verify Role Assignments

```bash
az role assignment list \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/<RESOURCE_GROUP>/providers/Microsoft.Network/expressRouteCircuits/<CIRCUIT_NAME>" \
  --query "[].{Role:roleDefinitionName, PrincipalId:principalId, PrincipalType:principalType}" \
  -o table
```

Expected output:
```
Role               PrincipalId                           PrincipalType
-----------------  ------------------------------------  ----------------
Reader             xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx  ServicePrincipal
Monitoring Reader  xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx  ServicePrincipal
```

## Step 3: Deploy Monitoring Script

### 3.1 Transfer Script to Zabbix Server

From your management workstation:

```bash
# Linux/Mac
scp express-route-monitor.py <username>@<zabbix-server-ip>:/home/<username>/

# Windows (using PowerShell or Command Prompt with OpenSSH)
scp C:\path\to\express-route-monitor.py <username>@<zabbix-server-ip>:/home/<username>/
```

### 3.2 Move Script to Zabbix Directory

On the Zabbix server:

```bash
sudo mv /home/<username>/express-route-monitor.py /usr/lib/zabbix/externalscripts/
```

### 3.3 Set Permissions

```bash
sudo chmod +x /usr/lib/zabbix/externalscripts/express-route-monitor.py
sudo chown zabbix:zabbix /usr/lib/zabbix/externalscripts/express-route-monitor.py
```

### 3.4 Verify Permissions

```bash
ls -la /usr/lib/zabbix/externalscripts/express-route-monitor.py
```

Expected output:
```
-rwxrwxr-x 1 zabbix zabbix 5020 Dec  8 19:27 /usr/lib/zabbix/externalscripts/express-route-monitor.py
```

## Step 4: Verify Dependencies

### 4.1 Check Python Version

```bash
python3 --version
```

Required: Python 3.8 or higher

### 4.2 Verify Requests Module

```bash
python3 -c "import requests; print('requests OK')"
```

### 4.3 Install Requests (if needed)

**Debian/Ubuntu:**
```bash
sudo apt-get install python3-requests
```

**RHEL/CentOS:**
```bash
sudo yum install python3-requests
```

**Using pip:**
```bash
sudo pip3 install requests
```

## Step 5: Obtain Azure Resource Credentials

Before running the monitoring script, you need to gather three pieces of information from your Azure environment.

### 5.1 Subscription ID

Get your Azure subscription ID:

```bash
az account show --query id -o tsv
```

Example output:
```
xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

Alternatively, view all subscriptions:

```bash
az account list --query "[].{name:name, id:id, state:state}" -o table
```

### 5.2 Resource Group Name

Identify the resource group where your ExpressRoute circuit is located. You can find this in:

- Azure Portal: Navigate to your ExpressRoute circuit
- Azure CLI: List resource groups

```bash
az group list --query "[].name" -o table
```

Example: `MyExpressRouteResourceGroup`

### 5.3 ExpressRoute Circuit Name

Get the name of your ExpressRoute circuit:

```bash
az network express-route list --resource-group <YOUR_RESOURCE_GROUP> --query "[].name" -o table
```

Example: `MyExpressRouteCircuit`

### 5.4 Example Parameters

For this guide, the following example placeholders are used:

| Parameter | Placeholder |
|-----------|-------------|
| Subscription ID | `<SUBSCRIPTION_ID>` |
| Resource Group | `<RESOURCE_GROUP>` |
| Circuit Name | `<CIRCUIT_NAME>` |

## Step 6: Test the Monitoring Script

The script requires three command-line arguments in the following order:

1. Subscription ID
2. Resource Group name
3. ExpressRoute Circuit name

### 6.1 Script Syntax

```bash
sudo -u zabbix python3 /usr/lib/zabbix/externalscripts/express_route_monitor.py <SUBSCRIPTION_ID> <RESOURCE_GROUP> <CIRCUIT_NAME>
```

### 6.2 Run the Script

Using your actual Azure credentials:

```bash
sudo -u zabbix python3 /usr/lib/zabbix/externalscripts/express_route_monitor.py <SUBSCRIPTION_ID> <RESOURCE_GROUP> <CIRCUIT_NAME>
```

### Expected Output

```json
{
    "data": {
        "name": "MyExpressRouteCircuit",
        "location": "eastus",
        "sku": {
            "name": "Standard_MeteredData",
            "tier": "Standard",
            "family": "MeteredData"
        },
        "circuitProvisioningState": "Enabled",
        "provisioningState": "Succeeded",
        "globalReachEnabled": false,
        "serviceProviderProperties": {
            "serviceProviderName": "Your Service Provider",
            "peeringLocation": "Location",
            "bandwidthInMbps": 1000
        },
        "bandwidthInGbps": null,
        "expressRoutePort": null,
        "allowClassicOperations": false,
        "serviceKey": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "serviceProviderProvisioningState": "Provisioned",
        "peerings": [
            {
                "name": "AzurePrivatePeering",
                "type": "AzurePrivatePeering",
                "provisioningState": "Succeeded",
                "state": "Enabled",
                "primaryBytesIn": null,
                "primaryBytesOut": null,
                "secondaryBytesIn": null,
                "secondaryBytesOut": null,
                "azureASN": 12076,
                "peerASN": 65000,
                "primaryPeerAddressPrefix": "10.0.0.0/30",
                "secondaryPeerAddressPrefix": "10.0.0.4/30"
            }
        ],
        "authorizations": [],
        "metrics": {
            "BitsInPerSecond": 50000000,
            "BitsOutPerSecond": 75000000,
            "IngressBandwidthUtilization": 12.5,
            "EgressBandwidthUtilization": 18.75,
            "ArpAvailability": 100,
            "BgpAvailability": 100
        },
        "healthStatus": "Healthy"
    }
}
```

**Note**: The output includes comprehensive circuit configuration, peering details, real-time metrics, and calculated health status.

## Monitored Metrics

The script collects the following metrics:

| Metric | Description | Unit |
|--------|-------------|------|
| BitsInPerSecond | Ingress throughput | bits/s |
| BitsOutPerSecond | Egress throughput | bits/s |
| ArpAvailability | ARP availability percentage | % |
| BgpAvailability | BGP availability percentage | % |
| IngressBandwidthUtilization | Ingress bandwidth utilization percentage | % |
| EgressBandwidthUtilization | Egress bandwidth utilization percentage | % |

## Script Features

The `express_route_monitor.py` script provides:

- **Managed Identity Authentication**: Securely authenticates using Azure VM's managed identity (no credentials in code)
- **Comprehensive Circuit Data**: Retrieves complete ExpressRoute circuit properties including SKU, provisioning state, and peering details
- **Real-time Metrics**: Collects performance metrics over a 5-minute window from Azure Monitor
- **Health Status**: Determines circuit health using Azure Resource Health API with fallback to metrics-based calculation
- **JSON Output**: Returns structured JSON output optimized for Zabbix parsing
- **Error Handling**: Provides clear error messages and appropriate exit codes

### Health Status Logic

The script determines health status using the following priority:

1. **Azure Resource Health API** (primary): Maps availability states to health status
   - `Available` → `Healthy`
   - `Degraded` → `Degraded`
   - `Unavailable` → `Unhealthy`
   - `Unknown` → `Unknown`

2. **Metrics-based Calculation** (fallback): Uses ARP and BGP availability
   - Both at 100% → `Healthy`
   - Either below 50% → `Unhealthy`
   - Either below 100% → `Degraded`
   - Otherwise → `Unknown`

## Step 7: Configure Zabbix Template

### 7.1 Import the Zabbix Template

The Zabbix template is provided in three formats: XML, JSON, and YAML. Choose the format compatible with your Zabbix version.

#### Import via Web Interface

1. Log in to your Zabbix web interface
2. Navigate to **Configuration** → **Templates**
3. Click **Import** in the top-right corner
4. Click **Choose File** and select one of the template files:
   - `zbx_er_template.xml` (recommended for most versions)
   - `zbx_er_template.json`
   - `zbx_er_template.yaml`
5. Review the import options:
   - Check **Create new** for templates, groups, and items
   - Check **Update existing** if reimporting
6. Click **Import**

#### Verify Import

After import, you should see:
- Template name: **Template Azure ExpressRoute**
- Group: **Virtual machines**
- Items: 11 total (1 master item + 10 dependent items)
- Triggers: 8 configured triggers
- Macros: 3 user macros

### 7.2 Template Components

#### Master Item (External Check)

| Property | Value |
|----------|-------|
| **Name** | ExpressRoute Circuit - Raw Data |
| **Type** | External check |
| **Key** | `express_route_monitor.py["{$AZ_SUBSCRIPTION}","{$AZ_RG}","{$AZ_ER_CIRCUIT}"]` |
| **Update interval** | 1m (default, configurable) |
| **Value type** | Text |
| **Description** | Executes the Python script and retrieves complete ExpressRoute circuit data in JSON format |

This master item calls the monitoring script with three parameters (subscription ID, resource group, circuit name) and stores the raw JSON response.

#### Dependent Items

All other items use JSON path preprocessing to extract specific values from the master item's output:

##### Performance Metrics

| Item Name | Key | Type | Units | JSON Path | Description |
|-----------|-----|------|-------|-----------|-------------|
| **ExpressRoute - Bits In Per Second** | `expressroute.bitsinpersecond` | Numeric (float) | bps | `$.data.metrics.BitsInPerSecond` | Ingress throughput in bits per second |
| **ExpressRoute - Bits Out Per Second** | `expressroute.bitsoutpersecond` | Numeric (float) | bps | `$.data.metrics.BitsOutPerSecond` | Egress throughput in bits per second |
| **ExpressRoute - Ingress Bandwidth Utilization** | `expressroute.ingressbandwidthutilization` | Numeric (float) | % | `$.data.metrics.IngressBandwidthUtilization` | Percentage of ingress bandwidth being utilized |
| **ExpressRoute - Egress Bandwidth Utilization** | `expressroute.egressbandwidthutilization` | Numeric (float) | % | `$.data.metrics.EgressBandwidthUtilization` | Percentage of egress bandwidth being utilized |

##### Availability Metrics

| Item Name | Key | Type | Units | JSON Path | Description |
|-----------|-----|------|-------|-----------|-------------|
| **ExpressRoute - ARP Availability** | `expressroute.arpavailability` | Numeric (float) | % | `$.data.metrics.ArpAvailability` | ARP (Address Resolution Protocol) availability percentage |
| **ExpressRoute - BGP Availability** | `expressroute.bgpavailability` | Numeric (float) | % | `$.data.metrics.BgpAvailability` | BGP (Border Gateway Protocol) availability percentage |

##### Status Items

| Item Name | Key | Type | JSON Path | Description |
|-----------|-----|------|-----------|-------------|
| **ExpressRoute Circuit - Name** | `expressroute.name` | Character | `$.data.name` | Name of the ExpressRoute circuit |
| **ExpressRoute - Circuit Provisioning State** | `expressroute.provisioningstate` | Character | `$.data.circuitProvisioningState` | Azure provisioning state (should be "Enabled") |
| **ExpressRoute - Service Provider State** | `expressroute.providerprovisioningstate` | Character | `$.data.serviceProviderProvisioningState` | Service provider provisioning state (should be "Provisioned") |
| **ExpressRoute - Health Status** | `expressroute.healthstatus` | Character | `$.data.healthStatus` | Overall health status: Healthy, Degraded, Unhealthy, or Unknown |

### 7.3 Configured Triggers

The template includes 8 triggers for automated alerting:

#### Critical (DISASTER Priority)

| Trigger Name | Expression | Description |
|--------------|------------|-------------|
| **ExpressRoute Circuit is Unhealthy** | `{last()}="Unhealthy"` | Fires when health status indicates the circuit is unhealthy |
| **ExpressRoute Circuit is Degraded** | `{last()}="Degraded"` | Fires when health status indicates degraded performance |
| **ExpressRoute Circuit is Unavailable** | `{last()}="Unavailable"` | Fires when health status indicates the circuit is unavailable |

#### High Priority

| Trigger Name | Expression | Description |
|--------------|------------|-------------|
| **ExpressRoute ARP Availability < 50%** | `{last()}<50` | Fires when ARP availability drops below 50% |
| **ExpressRoute BGP Availability < 50%** | `{last()}<50` | Fires when BGP availability drops below 50% |
| **ExpressRoute Ingress Utilization > 95%** | `{last()}>95` | Fires when ingress bandwidth utilization exceeds 95% |
| **ExpressRoute Egress Utilization > 95%** | `{last()}>95` | Fires when egress bandwidth utilization exceeds 95% |
| **ExpressRoute Circuit is not Enabled** | `{last()}<>"Enabled"` | Fires when circuit provisioning state is not "Enabled" |
| **ExpressRoute Circuit is not Provisioned** | `{last()}<>"Provisioned"` | Fires when service provider state is not "Provisioned" |

### 7.4 Template Macros

The template uses three user macros that must be configured for each host:

| Macro | Description | Example Value |
|-------|-------------|---------------|
| **{$AZ_SUBSCRIPTION}** | Azure Subscription ID where the ExpressRoute circuit is located | `12345678-1234-1234-1234-123456789abc` |
| **{$AZ_RG}** | Azure Resource Group name containing the ExpressRoute circuit | `MyExpressRouteRG` |
| **{$AZ_ER_CIRCUIT}** | ExpressRoute Circuit name to monitor | `MyExpressRouteCircuit` |

These macros are referenced in the master item's key parameter and are passed as arguments to the monitoring script.

### 7.5 Create a Host for ExpressRoute Monitoring

#### 7.5.1 Create New Host

1. Navigate to **Configuration** → **Hosts**
2. Click **Create host** in the top-right corner
3. Configure the host:
   - **Host name**: `Azure ExpressRoute - <Circuit Name>` (e.g., `Azure ExpressRoute - Production`)
   - **Visible name**: Same as host name or a friendly name
   - **Groups**: Select **Virtual machines** (or create a new group like "Azure ExpressRoute")
   - **Interfaces**: 
     - Since this uses external scripts, the agent interface is optional
     - You can add a dummy IP (e.g., `127.0.0.1`) or leave it empty
4. Click **Add**

#### 7.5.2 Link Template to Host

1. Go to the newly created host
2. Click the **Templates** tab
3. In the **Link new templates** field, start typing "Azure ExpressRoute"
4. Select **Template Azure ExpressRoute**
5. Click **Add** (under the template selection)
6. Click **Update** to save

#### 7.5.3 Configure Host Macros

1. On the host configuration page, go to the **Macros** tab
2. You'll see three inherited macros from the template (they appear with `{$...}` notation)
3. Click **Inherited and host macros** to expand the view
4. Configure each macro with your Azure values:

   | Macro | Value |
   |-------|-------|
   | `{$AZ_SUBSCRIPTION}` | Your Azure subscription ID |
   | `{$AZ_RG}` | Your resource group name |
   | `{$AZ_ER_CIRCUIT}` | Your ExpressRoute circuit name |

   Example:
   ```
   {$AZ_SUBSCRIPTION} = 12345678-abcd-efgh-ijkl-123456789012
   {$AZ_RG} = Production-Network-RG
   {$AZ_ER_CIRCUIT} = ER-Circuit-Primary
   ```

5. Click **Update** to save

### 7.6 Verify Monitoring

#### 7.6.1 Check Latest Data

1. Navigate to **Monitoring** → **Latest data**
2. Filter by your host name
3. You should see all 11 items collecting data
4. The **ExpressRoute Circuit - Raw Data** item should show the full JSON output
5. All dependent items should show extracted values

#### 7.6.2 Verify Items Are Working

After some minutes, check that:
- All items show recent timestamps
- Numeric values are reasonable (e.g., availability near 100%, non-zero throughput)
- Status items show expected values ("Enabled", "Provisioned", "Healthy")
- No "Not supported" or error messages

#### 7.6.3 Test Triggers

You can verify triggers are working:
1. Navigate to **Monitoring** → **Problems**
2. Any active issues with the ExpressRoute circuit will appear here
3. Check trigger expressions in **Configuration** → **Hosts** → [Your Host] → **Triggers**

### 7.7 Monitoring Multiple Circuits

To monitor multiple ExpressRoute circuits:

#### Option 1: Multiple Hosts (Recommended)

Create a separate host for each circuit:
1. Follow steps 7.5.1 through 7.5.3 for each circuit
2. Use descriptive host names (e.g., `Azure ER - Production`, `Azure ER - DR`)
3. Configure different macro values for each host

**Benefits:**
- Clear separation of monitoring data
- Individual trigger states per circuit
- Easy to disable monitoring for specific circuits
- Better for reporting and dashboards

#### Option 2: Multiple Items on Single Host

Create multiple instances of items on a single host:
1. Clone the template items manually
2. Modify the keys and master item parameters
3. Create separate macros for each circuit (e.g., `{$AZ_ER_CIRCUIT_1}`, `{$AZ_ER_CIRCUIT_2}`)

**Note:** This approach is more complex and not recommended unless you have specific requirements.

### 7.8 Customization Options

#### 7.8.1 Adjust Update Interval

To change how frequently the script runs:
1. Go to **Configuration** → **Hosts** → [Your Host] → **Items**
2. Click on **ExpressRoute Circuit - Raw Data** (the master item)
3. Modify the **Update interval** field (default: 1m)
4. Recommended intervals:
   - Production monitoring: 1-2 minutes
   - Development/testing: 5 minutes
   - Low-priority circuits: 10 minutes
5. Click **Update**

**Note:** All dependent items will automatically update when the master item updates.

#### 7.8.2 Modify Trigger Thresholds

To adjust alert thresholds:
1. Navigate to **Configuration** → **Hosts** → [Your Host] → **Triggers**
2. Click on the trigger you want to modify
3. Edit the **Expression** field

Examples:
- Change bandwidth utilization threshold from 95% to 80%:
  ```
  {Template Azure ExpressRoute:expressroute.ingressbandwidthutilization.last()}>80
  ```
- Change ARP availability threshold from 50% to 70%:
  ```
  {Template Azure ExpressRoute:expressroute.arpavailability.last()}<70
  ```

#### 7.8.3 Disable Specific Triggers

If certain triggers are not relevant:
1. Go to **Configuration** → **Hosts** → [Your Host] → **Triggers**
2. Find the trigger to disable
3. Change **Status** from **Enabled** to **Disabled**
4. Click **Update**

#### 7.8.4 Add Custom Items

To monitor additional data from the JSON output:
1. Create a new item
2. Set **Type** to **Dependent item**
3. Set **Master item** to `express_route_monitor.py["{$AZ_SUBSCRIPTION}","{$AZ_RG}","{$AZ_ER_CIRCUIT}"]`
4. Add preprocessing step:
   - **Type**: JSONPath
   - **Parameters**: Your desired JSON path (e.g., `$.data.sku.tier`)
5. Configure remaining item properties (type, units, etc.)

## Troubleshooting

### Script Returns No Data or Errors

If you encounter issues with the script not returning data:

#### 1. Install dos2unix (if transferring from Windows)

Line ending issues from Windows can cause problems:

```bash
sudo apt-get update
sudo apt-get install dos2unix -y
```

#### 2. Convert Line Endings

```bash
sudo dos2unix /usr/lib/zabbix/externalscripts/express_route_monitor.py
```

#### 3. Reset Permissions

```bash
sudo chmod +x /usr/lib/zabbix/externalscripts/express_route_monitor.py
sudo chown zabbix:zabbix /usr/lib/zabbix/externalscripts/express_route_monitor.py
```

#### 4. Test Again

```bash
sudo -u zabbix python3 /usr/lib/zabbix/externalscripts/express_route_monitor.py <SUBSCRIPTION_ID> <RESOURCE_GROUP> <CIRCUIT_NAME>
```

### Common Issues

**Issue: "No module named 'requests'"**
- Solution: Install python3-requests package

**Issue: "Permission denied"**
- Solution: Verify script has execute permissions and is owned by zabbix user

**Issue: "Authentication failed"**
- Solution: Verify Managed Identity is properly configured and has required role assignments

**Issue: "Resource not found"**
- Solution: Verify the ExpressRoute circuit resource path and ensure you have the correct subscription ID, resource group, and circuit name

## Security Considerations

- **No Credentials Required**: Uses Azure Managed Identity for authentication
- **Least Privilege**: Only Reader and Monitoring Reader roles are assigned
- **Scope Limited**: Permissions are scoped to specific ExpressRoute circuit resources
- **Secure by Default**: No secrets or keys stored in configuration files

## Security Considerations

- **No Credentials Required**: Uses Azure Managed Identity for authentication
- **Least Privilege**: Only Reader and Monitoring Reader roles are assigned
- **Scope Limited**: Permissions are scoped to specific ExpressRoute circuit resources
- **Secure by Default**: No secrets or keys stored in configuration files

## Integration with Zabbix

The complete integration workflow:

1. **Script Deployment**: Monitor script placed in Zabbix external scripts directory
2. **Template Import**: Zabbix template defining items, triggers, and macros
3. **Host Creation**: Individual hosts created for each ExpressRoute circuit
4. **Macro Configuration**: Azure credentials configured per host
5. **Data Collection**: Zabbix executes script at defined intervals
6. **Metric Extraction**: Dependent items parse JSON output
7. **Alerting**: Triggers fire based on configured thresholds
8. **Visualization**: Graphs and dashboards display metrics

## Additional Resources

- [Azure Managed Identity Documentation](https://docs.microsoft.com/azure/active-directory/managed-identities-azure-resources/)
- [Azure ExpressRoute Monitoring](https://docs.microsoft.com/azure/expressroute/expressroute-monitoring-metrics-alerts)
- [Zabbix External Checks](https://www.zabbix.com/documentation/current/manual/config/items/itemtypes/external)
- [Zabbix Template Documentation](https://www.zabbix.com/documentation/current/manual/config/templates)
- [Zabbix JSON Preprocessing](https://www.zabbix.com/documentation/current/manual/config/items/preprocessing/jsonpath_functionality)

## Support

For issues or questions:
- Check Azure role assignments are correct
- Verify Managed Identity is enabled on the VM
- Review Zabbix server logs for errors
- Ensure network connectivity to Azure management endpoints
- Verify external scripts are enabled in Zabbix configuration
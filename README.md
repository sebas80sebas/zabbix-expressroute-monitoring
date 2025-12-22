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

## Integration with Zabbix

Once the script is working correctly, you can integrate it with Zabbix by:

1. Creating a new host for the ExpressRoute circuit
2. Adding external check items that call the script
3. Setting up triggers based on metric thresholds
4. Configuring graphs and dashboards

## Additional Resources

- [Azure Managed Identity Documentation](https://docs.microsoft.com/azure/active-directory/managed-identities-azure-resources/)
- [Azure ExpressRoute Monitoring](https://docs.microsoft.com/azure/expressroute/expressroute-monitoring-metrics-alerts)
- [Zabbix External Checks](https://www.zabbix.com/documentation/current/manual/config/items/itemtypes/external)

## Support

For issues or questions:
- Check Azure role assignments are correct
- Verify Managed Identity is enabled on the VM
- Review Zabbix server logs for errors
- Ensure network connectivity to Azure management endpoints
  

# zabbix-azure-expressroute-monitoring

### Environment requirements
The script uses Managed Identity (IMDS 169.254.169.254) for authentication; therefore it must be executed on a VM or resource with MSI enabled and with the appropriate permissions on the subscription. Make sure the role (e.g., Reader on the subscription and permissions for Microsoft.Insights/metrics/read) is assigned to the managed identity principal.

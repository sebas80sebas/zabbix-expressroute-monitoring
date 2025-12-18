# zabbix-azure-expressroute-monitoring

### Environment requirements
The script uses Managed Identity (IMDS 169.254.169.254) for authentication; therefore it must be executed on a VM or resource with MSI enabled and with the appropriate permissions on the subscription. Make sure the role (e.g., Reader on the subscription and permissions for Microsoft.Insights/metrics/read) is assigned to the managed identity principal.

It is necessary that the script uses LF (Line Feed) line endings. If the file was created or edited on Windows and contains CRLF line endings, it may fail to run correctly on Unix/Linux systems. In that case, convert it to LF format using a tool like dos2unix before executing it.

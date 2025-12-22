#!/usr/bin/python3
# -*- coding: utf-8 -*-

import requests
import sys
import json
import argparse
from datetime import datetime, timedelta

# ====================================================================
# Obtain an Azure access token using Managed Identity (MSI)
# ====================================================================
def get_token():
    TOKEN_URL = "http://169.254.169.254/metadata/identity/oauth2/token"
    params = {
        "api-version": "2018-02-01",
        "resource": "https://management.azure.com/"
    }
    headers = {"Metadata": "true"}

    try:
        # Call the Azure Instance Metadata Service to get an access token
        response = requests.get(TOKEN_URL, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        # Return a JSON-formatted error if token retrieval fails
        print(json.dumps({"error": f"Error getting token: {e}"}))
        return None

# ====================================================================
# Query ExpressRoute Circuit details (API version 2025-01-01)
# ====================================================================
def get_expressroute_circuit(subscription_id, resource_group, circuit_name):
    token = get_token()
    if not token:
        return None, 1  # Token error

    url = (
        f"https://management.azure.com/subscriptions/{subscription_id}"
        f"/resourceGroups/{resource_group}"
        f"/providers/Microsoft.Network/expressRouteCircuits/{circuit_name}"
    )
    params = {"api-version": "2025-01-01"}
    headers = {"Authorization": f"Bearer {token}"}

    try:
        # Query ExpressRoute circuit properties
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json(), 0
    except Exception as e:
        # Return error code 2 if the API call fails
        return {"error": f"Error querying ExpressRoute: {e}"}, 2

# ====================================================================
# Query Azure Resource Health for the ExpressRoute Circuit
# ====================================================================
def get_resource_health(subscription_id, resource_group, circuit_name):
    token = get_token()
    if not token:
        return None

    resource_uri = (
        f"/subscriptions/{subscription_id}"
        f"/resourceGroups/{resource_group}"
        f"/providers/Microsoft.Network/expressRouteCircuits/{circuit_name}"
    )
    url = (
        f"https://management.azure.com{resource_uri}"
        f"/providers/Microsoft.ResourceHealth/availabilityStatuses/current"
    )
    params = {"api-version": "2023-07-01"}
    headers = {"Authorization": f"Bearer {token}"}

    try:
        # Retrieve current resource health status
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception:
        # Fail silently to allow fallback using metrics-based health
        return None

# ====================================================================
# Query Azure Monitor metrics for the ExpressRoute Circuit
# ====================================================================
def get_expressroute_metrics(subscription_id, resource_group, circuit_name):
    token = get_token()
    if not token:
        return {}

    resource_id = (
        f"/subscriptions/{subscription_id}"
        f"/resourceGroups/{resource_group}"
        f"/providers/Microsoft.Network/expressRouteCircuits/{circuit_name}"
    )
    url = f"https://management.azure.com{resource_id}/providers/microsoft.insights/metrics"

    # Define a 5-minute time window ending now (UTC)
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=5)
    timespan = "{}/{}".format(
        start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    params = {
        "api-version": "2018-01-01",
        "timespan": timespan,
        "interval": "PT1M",
        "metricnames": (
            "BitsInPerSecond,BitsOutPerSecond,"
            "IngressBandwidthUtilization,EgressBandwidthUtilization,"
            "ArpAvailability,BgpAvailability"
        ),
        "aggregation": "Average,Maximum"
    }
    headers = {"Authorization": f"Bearer {token}"}

    try:
        # Retrieve Azure Monitor metrics
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        # Log warning but do not fail execution
        print(json.dumps({"warning": f"Error querying metrics: {e}"}))
        return {}

# ====================================================================
# Parse Azure Monitor metrics and extract latest values
# ====================================================================
def parse_metrics(metrics_data):
    if not metrics_data or "value" not in metrics_data:
        return {}

    parsed_metrics = {}

    for metric in metrics_data.get("value", []):
        metric_name = metric.get("name", {}).get("value")
        timeseries = metric.get("timeseries", [])
        if not timeseries:
            continue

        # Use the most recent available data point (average preferred, fallback to maximum)
        data_points = timeseries[0].get("data", [])
        if data_points:
            latest_value = None
            for point in reversed(data_points):
                if point.get("average") is not None:
                    latest_value = point.get("average")
                    break
                elif point.get("maximum") is not None:
                    latest_value = point.get("maximum")
                    break

            if latest_value is not None:
                parsed_metrics[metric_name] = latest_value

    return parsed_metrics

# ====================================================================
# Parse Azure Resource Health status
# ====================================================================
def parse_health_status(health_data):
    if not health_data:
        return None

    properties = health_data.get("properties", {})
    availability_state = properties.get("availabilityState", "Unknown")

    # Map Azure availability states to simplified health states
    health_mapping = {
        "Available": "Healthy",
        "Unavailable": "Unhealthy",
        "Degraded": "Degraded",
        "Unknown": "Unknown"
    }

    return health_mapping.get(availability_state, "Unknown")

# ====================================================================
# Calculate health status based on ARP and BGP availability metrics
# ====================================================================
def calculate_health_from_metrics(metrics):
    if not metrics:
        return "Unknown"

    arp_availability = metrics.get("ArpAvailability", 0)
    bgp_availability = metrics.get("BgpAvailability", 0)

    if arp_availability == 100 and bgp_availability == 100:
        return "Healthy"
    if arp_availability < 50 or bgp_availability < 50:
        return "Unhealthy"
    if arp_availability < 100 or bgp_availability < 100:
        return "Degraded"

    return "Unknown"

# ====================================================================
# Parse all relevant ExpressRoute Circuit properties
# ====================================================================
def parse_expressroute_data(data):
    if not data or isinstance(data, dict) and data.get("error"):
        return data if isinstance(data, dict) else {}

    props = data.get("properties", {})
    parsed_peerings = []

    for p in props.get("peerings", []):
        pd = p.get("properties", {})
        stats = pd.get("stats", {})

        parsed_peerings.append({
            "name": p.get("name"),
            "type": pd.get("peeringType"),
            "provisioningState": pd.get("provisioningState"),
            "state": pd.get("state"),
            "primaryBytesIn": stats.get("primarybytesIn"),
            "primaryBytesOut": stats.get("primarybytesOut"),
            "secondaryBytesIn": stats.get("secondarybytesIn"),
            "secondaryBytesOut": stats.get("secondarybytesOut"),
            "azureASN": pd.get("azureASN"),
            "peerASN": pd.get("peerASN"),
            "primaryPeerAddressPrefix": pd.get("primaryPeerAddressPrefix"),
            "secondaryPeerAddressPrefix": pd.get("secondaryPeerAddressPrefix"),
        })

    parsed_authorizations = [
        {
            "id": a.get("id"),
            "name": a.get("name"),
            "provisioningState": a.get("properties", {}).get("provisioningState")
        }
        for a in props.get("authorizations", [])
    ]

    return {
        "name": data.get("name"),
        "location": data.get("location"),
        "sku": data.get("sku"),
        "circuitProvisioningState": props.get("circuitProvisioningState"),
        "provisioningState": props.get("provisioningState"),
        "globalReachEnabled": props.get("globalReachEnabled"),
        "serviceProviderProperties": props.get("serviceProviderProperties"),
        "bandwidthInGbps": props.get("bandwidthInGbps"),
        "expressRoutePort": props.get("expressRoutePort"),
        "allowClassicOperations": props.get("allowClassicOperations"),
        "serviceKey": props.get("serviceKey"),
        "serviceProviderProvisioningState": props.get("serviceProviderProvisioningState"),
        "peerings": parsed_peerings,
        "authorizations": parsed_authorizations
    }

# ====================================================================
# Main execution logic
# ====================================================================
def main():
    parser = argparse.ArgumentParser(
        description="ExpressRoute monitor: returns JSON with properties, metrics, and health status."
    )
    parser.add_argument("subscription_id", help="Subscription ID (GUID)")
    parser.add_argument("resource_group", help="Resource Group name")
    parser.add_argument("circuit_name", help="ExpressRoute Circuit name")

    args = parser.parse_args()

    # 1) Retrieve ExpressRoute circuit information
    raw, rc = get_expressroute_circuit(
        args.subscription_id,
        args.resource_group,
        args.circuit_name
    )

    if rc == 1:
        # Token acquisition error
        print(json.dumps({"error": "Failed to obtain MSI token."}))
        sys.exit(1)
    elif rc == 2 and isinstance(raw, dict) and raw.get("error"):
        print(json.dumps(raw))
        sys.exit(2)

    parsed = parse_expressroute_data(raw)

    # 2) Retrieve and parse metrics
    metrics_raw = get_expressroute_metrics(
        args.subscription_id,
        args.resource_group,
        args.circuit_name
    )
    metrics = parse_metrics(metrics_raw)
    parsed["metrics"] = metrics

    # 3) Determine health status (API first, metrics as fallback)
    health_raw = get_resource_health(
        args.subscription_id,
        args.resource_group,
        args.circuit_name
    )
    health_status_from_api = parse_health_status(health_raw)
    health_status_from_metrics = calculate_health_from_metrics(metrics)

    parsed["healthStatus"] = (
        health_status_from_api if health_status_from_api else health_status_from_metrics
    )

    # Output JSON formatted for Zabbix consumption
    json_output = json.dumps({"data": parsed}, indent=4)
    print(json_output)
    sys.exit(0)

# ====================================================================
# Script entry point
# ====================================================================
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Catch any unexpected errors
        print(json.dumps({"error": f"Unexpected error: {e}"}))
        sys.exit(3)


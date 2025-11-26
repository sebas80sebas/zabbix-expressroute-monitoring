#!/usr/bin/python3
import json
import sys
import time
import random
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

LOG_FILE = "/var/log/zabbix/expressroute_simulated.log"

# ============================================================
# BASIC LOGGING FUNCTION
# ============================================================

def log_message(message, level="INFO"):
    """Write logs for debugging purposes"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}\n"
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_entry)
    except:
        pass  # Ignore logging errors silently

# ============================================================
# SIMULATED RESPONSE GENERATOR
# ============================================================

def get_simulated_response(circuit_name):
    """
    Generate realistic simulated data for ExpressRoute monitoring.
    Values vary randomly to test Zabbix triggers and alerts.
    """

    # Simulate RPO variation
    base_rpo = 150
    rpo_variation = random.randint(-50, 200)
    rpo_value = max(0, base_rpo + rpo_variation)

    # Simulate circuit state
    states = ["Enabled", "Provisioning", "Disabled"]
    circuit_state = random.choice(states)

    # Simulate BGP state
    bgp_states = ["Connected", "Connecting", "NotConnected"]
    bgp_state = random.choice(bgp_states)

    # Simulate availability percentages
    arp_availability = random.uniform(95.0, 100.0)
    bgp_availability = random.uniform(95.0, 100.0)

    # Simulate bandwidth usage
    bandwidth_in = random.uniform(50, 950)
    bandwidth_out = random.uniform(30, 800)

    # Simulate latency
    latency = random.uniform(5, 50)

    result = {
        "data": [
            {
                "HOSTNAME": circuit_name,
                "RPO": rpo_value,
                "CIRCUIT_STATE": circuit_state,
                "BGP_STATE": bgp_state,
                "ARP_AVAILABILITY": round(arp_availability, 2),
                "BGP_AVAILABILITY": round(bgp_availability, 2),
                "BANDWIDTH_IN_MBPS": round(bandwidth_in, 2),
                "BANDWIDTH_OUT_MBPS": round(bandwidth_out, 2),
                "LATENCY_MS": round(latency, 2),
                "TIMESTAMP": int(time.time()),
                "STATUS": "OK" if circuit_state == "Enabled" and bgp_state == "Connected" else "WARNING"
            }
        ],
        "metadata": {
            "mode": "simulated",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0"
        }
    }

    log_message(f"Simulated data generated - RPO: {rpo_value}, State: {circuit_state}")
    return result

# ============================================================
# MAIN ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: expressroute_simulated.py <circuit_name>"}))
        sys.exit(1)

    circuit_name = sys.argv[1]
    response = get_simulated_response(circuit_name)
    print(json.dumps(response, indent=2))

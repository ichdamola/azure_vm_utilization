import csv
from datetime import datetime, timedelta

from azure.mgmt.compute import ComputeManagementClient
from azure.identity import DefaultAzureCredential
from azure.mgmt.monitor import MonitorManagementClient


# Utilization
subscription_id = "your_subscription_id"
resource_group_name = "your_resource_group_name"
vm_name = "your_vm_name"

credential = DefaultAzureCredential()
monitor_client = MonitorManagementClient(credential, subscription_id)

# Get the start and end times for the query (last 30 days)
end_time = datetime.utcnow()
start_time = end_time - timedelta(days=30)

# Define the query to get the utilization metrics
query = f"""union 
InsightsMetrics | where Name == 'Percentage CPU' 
| where ResourceId == '/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Compute/virtualMachines/{vm_name}'
| where TimeGenerated >= datetime('{start_time.isoformat()}Z') and TimeGenerated <= datetime('{end_time.isoformat()}Z') 
| summarize avg(Val) by bin(TimeGenerated, 1h), bin(ResourceId, 1s) | extend MetricName = 'CPU Utilization' 
,
InsightsMetrics | where Name == 'Available Memory Bytes' 
| where ResourceId == '/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Compute/virtualMachines/{vm_name}' 
| where TimeGenerated >= datetime('{start_time.isoformat()}Z') and TimeGenerated <= datetime('{end_time.isoformat()}Z') 
| summarize avg(Val / 1024 / 1024 / 1024) by bin(TimeGenerated, 1h), bin(ResourceId, 1s) | extend MetricName = 'Memory Utilization' 
,
InsightsMetrics | where Name == 'LogicalDisk Used Percentage' 
| where ResourceId contains 'virtualMachines' and ResourceId contains '{vm_name}'
| where TimeGenerated >= datetime('{start_time.isoformat()}Z') and TimeGenerated <= datetime('{end_time.isoformat()}Z') 
| summarize avg(Val) by bin(TimeGenerated, 1h), bin(ResourceId, 1s) | extend MetricName = 'Disk Utilization' """

results = monitor_client.metrics.list(
    resource_id=f"/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Compute/virtualMachines/{vm_name}",
    metric_names=[
        "Percentage CPU",
        "Available Memory Bytes",
        "LogicalDisk Used Percentage",
    ],
    start_time=start_time,
    end_time=end_time,
    interval="PT1H",
)

# Extract the utilization data from the results and write it to a CSV file
with open("utilization.csv", mode="w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["Timestamp", "Metric Name", "Value"])
    for result in results.value:
        timestamp = datetime.fromisoformat(result.time_stamp).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        metric_name = result.MetricName
        value = round(result.average, 2)
        writer.writerow([timestamp, metric_name, value])

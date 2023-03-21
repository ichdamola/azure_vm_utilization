import csv
from datetime import datetime, timedelta

from azure.mgmt.compute import ComputeManagementClient
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.monitor.query import MetricsQueryClient
from azure.monitor.query.models import MetricAggregationType

from azure.mgmt.compute.models import VirtualMachine


# Get all VMs
TENANT_ID = "<your-tenant-id>"
CLIENT_ID = "<your-client-id>"
CLIENT_SECRET = "<your-client-secret>"
SUBSCRIPTION_ID = "<your-subscription-id>"

credentials = ClientSecretCredential(
    tenant_id=TENANT_ID, client_id=CLIENT_ID, client_secret=CLIENT_SECRET
)

compute_client = ComputeManagementClient(
    credentials=credentials, subscription_id=SUBSCRIPTION_ID
)

vms = compute_client.virtual_machines.list_all()

for vm in vms:
    print(vm.name)

# Utilization
subscription_id = "your_subscription_id"
resource_group_name = "your_resource_group_name"
vm_name = "your_vm_name"

credential = DefaultAzureCredential()
compute_client = ComputeManagementClient(credential, subscription_id)
query_client = MetricsQueryClient(credential)

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

# Execute the query and get the results
results = query_client.query_resource(
    query, endpoint="https://management.azure.com"
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

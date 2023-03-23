import csv
import os
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.monitor import MonitorManagementClient
from datetime import datetime, timedelta

# Replace with your subscription ID and resource group name
subscription_id = '<your-subscription-id>'
resource_group = '<your-resource-group>'

# Authenticate using the default credentials
credential = DefaultAzureCredential()

# Create a ComputeManagementClient and MonitorManagementClient instance
compute_client = ComputeManagementClient(
    credential=credential,
    subscription_id=subscription_id
)
monitor_client = MonitorManagementClient(
    credential=credential,
    subscription_id=subscription_id
)

# Get all VMs in the specified resource group
vms = compute_client.virtual_machines.list(resource_group)

# Define the CSV output file and write the headers
csv_filename = 'vm_metrics.csv'
with open(csv_filename, mode='w', newline='') as csv_file:
    fieldnames = ['subscription', 'resourcegroup', 'vm name', 'current size', 'cpu utilization', 'memory utilization', 'disk utilization']
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()

    # Iterate over the VMs and fetch the requested metrics for the past 30 days
    for vm in vms:
        vm_name = vm.name
        vm_rg = vm.id.split('/')[4]
        vm_size = vm.hardware_profile.vm_size
        cpu_query = "Percentage CPU"
        memory_query = "Percentage Memory"
        disk_query = "Percentage Disk Time"
        start_time = datetime.utcnow() - timedelta(days=30)
        end_time = datetime.utcnow()

        # Define the aggregation type and interval
        aggregation = "Average"
        interval = "P1D"

        # Fetch the CPU utilization metric data
        cpu_data = monitor_client.metrics.list(
            resource_id=f"/subscriptions/{subscription_id}/resourceGroups/{vm_rg}/providers/Microsoft.Compute/virtualMachines/{vm_name}",
            metricnames=cpu_query,
            starttime=start_time,
            endtime=end_time,
            interval=interval,
            aggregation=aggregation
        )

        # Fetch the memory utilization metric data
        memory_data = monitor_client.metrics.list(
            resource_id=f"/subscriptions/{subscription_id}/resourceGroups/{vm_rg}/providers/Microsoft.Compute/virtualMachines/{vm_name}",
            metricnames=memory_query,
            starttime=start_time,
            endtime=end_time,
            interval=interval,
            aggregation=aggregation
        )

        # Fetch the disk utilization metric data for each data disk
        for disk in vm.storage_profile.data_disks:
            disk_name = disk.name
            disk_data = monitor_client.metrics.list(
                resource_id=f"/subscriptions/{subscription_id}/resourceGroups/{vm_rg}/providers/Microsoft.Compute/virtualMachines/{vm_name}/disks/{disk_name}",
                metricnames=disk_query,
                starttime=start_time,
                endtime=end_time,
                interval=interval,
                aggregation=aggregation
            )

            # Calculate the average disk utilization percentage for the past 30 days
            disk_utilization_percent = sum([d.average for item in disk_data.value for timeseries in item.timeseries for d in timeseries.data]) / len(list(disk_data))

            # Fetch the current size of the VM
            vm_details = compute_client.virtual_machines.get(resource_group_name=vm_rg, vm_name=vm_name)
            current_size = vm_details.hardware_profile.vm_size

            # Calculate the average CPU utilization percentage for the past 30 days
            cpu_utilization_percent = sum([d.average for item in cpu_data.value for timeseries in item.timeseries for d in timeseries.data]) / len(list(cpu_data))

            # Calculate the average memory utilization percentage for the past 30 days
            memory_utilization_percent = sum([d.average for item in memory_data.value for timeseries in item.timeseries for d in timeseries.data]) / len(list(memory_data))


            # Write the metric values to the CSV file
            writer.writerow({
            'subscription': subscription_id,
            'resourcegroup': vm_rg,
            'vm name': vm_name,
            'current size': current_size,
            'cpu utilization': round(cpu_utilization_percent, 2),
            'memory utilization': round(memory_utilization_percent, 2),
            'disk utilization': round(disk_utilization_percent, 2)
        })
            

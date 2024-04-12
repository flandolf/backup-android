import subprocess

# Blue foreground
print("\033[34m")

print("Partition backup script for Android devices - by @flandolf")
print("Must have ADB installed, rooted device and USB debugging enabled")
print("This script will backup all partitions except userdata")

input("Backup folder will be created in the same directory as this script. Press Enter to continue...")

partitions = subprocess.check_output("adb shell su -c 'ls /dev/block/by-name/'", shell=True).split()

partitions = [partition.decode('utf-8') for partition in partitions]

slot = subprocess.check_output("adb shell su -c 'getprop ro.boot.slot_suffix'", shell=True).decode('utf-8').strip()

partitions = [partition for partition in partitions if partition.endswith(slot)]


for partition in partitions:
    print(partition)
print(slot)
input("Press Enter to continue...")

subprocess.call("adb shell su -c 'mkdir /storage/emulated/0/backup'", shell=True)
subprocess.call("mkdir backup", shell=True)

for partition in partitions:
    if partition == "userdata":
        continue
    print("Backing up", partition)
    subprocess.call(f"adb shell su -c 'dd if=/dev/block/by-name/{partition} of=/storage/emulated/0/backup/{partition}.img'", shell=True)
    subprocess.call(f"adb pull /storage/emulated/0/backup/{partition}.img backup/", shell=True)
    subprocess.call(f"adb shell su -c 'rm /storage/emulated/0/backup/{partition}.img'", shell=True)

subprocess.call("adb shell su -c 'rmdir /storage/emulated/0/backup'", shell=True)

print("Done!")
input("Press Enter to exit...")
print("\033[0m")
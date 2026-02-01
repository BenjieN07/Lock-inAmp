from zhinst.toolkit import Session

# LabOne Data Server settings (default)
HOST = "localhost"
PORT = 8004

# Connect to the LabOne Data Server
session = Session(HOST, PORT)

# Ask the server what devices it can see
devices = session.devices.visible()

print("Zurich Instruments devices visible to LabOne:")
if not devices:
    print("  (none found)")
else:
    for d in devices:
        print(" ", d)

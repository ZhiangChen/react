# Mission Planner Simulation

Mission Planner simulation can be used to simulate multiple UAVs for testing and mission preplanning with the REACT ground control station.

## Setup Instructions

### 1. Configure Mission Planner Simulation
- Launch **Mission Planner**
- Navigate to the **Simulation** tab
- Select **`Copter Swarm - Single Link`** to simulate multiple vehicles

### 2. Set Up MAVLink Forwarding
- Open the advanced configuration panel by pressing **`Ctrl + F`**
- Select **`MAVLink`** from the configuration options
- Configure the forwarding settings:
  - **Protocol**: UDP
  - **Direction**: Outbound  
  - **Enable Write**: ✓ (checked)
- Click **`GO`** to start MAVLink message forwarding

### 3. Configure REACT Connection
- Open the REACT **`config.yaml`** file
- Set the `telem1` routed address and port to match the Mission Planner forwarding settings:
  ```yaml
  telemetry1:
    routed_to:
      protocol: "udp"
      udp_address: "127.0.0.1"
      udp_port: 14552  # Match Mission Planner output port
  ```

### 4. Verify Connection
Once both systems are configured, REACT should successfully connect to the simulated vehicles from Mission Planner, allowing you to control and monitor multiple UAVs in the simulation environment. You can check the connection status from the log file. 
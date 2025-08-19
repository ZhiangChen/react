# REACT Hardware

## UAV
- Airframe: Holybro X650
- Flight controller: Holybro Pixhawk 6X
- RTK GPS: Holybro H-RTK F9P Ultralight
- Telem1 (main; bidirectional): Holybro P900 (902-928 MHz)
- Telem2 (secondary; unidirectional): Holybro SiK Telemetry Radio V3 (915Mhz or 433Mhz)
- RC receiver: DSMX Remote Receiver
- Imaging: Seagull #REC, Sony a6000
- Battery: Zeee semi-solid-state Li-ion baterry (6S 22.2V 10C 22000mAh)
- Power modules: Holybro PM02D, Holybro PDB 60A; Hobbywing UBEC 2A AIR (Mateksys Servo PDB, w/ 4A BEC 5.5-36V to 5-8.2V)

## Wiring
Telem1 -> Holybro P900  
Telem2 -> Sik Radio V3  
DSM -> DSM Remote Receiver  
GPS1 -> H-RTK F9P  
AUX PWM -> Seagull Channel 1 -> Sony a6000 Multi 

wiring diagram: https://drive.google.com/file/d/1E1OPYGeqIj-z81CuZiIEpoTUAfXG3kQr/view?usp=drive_link

## Imaging Module
Sony A6000 and Seagull REC: https://github.com/ZhiangChen/learning_field_robotics/blob/main/docs/sensors/cameras/Sony_camera.md


## GPS Module
Rover: Holybro H-RTK F9P Ultralight  
Base: Emlid RS3  


## Communication Module
Telem1: Holybro P900, multi-to-point telemetry, two-way communication   
Telem2: Sik Radio V3, point-to-point telemetry, one-way communication 
RC: Spektrum iX20  
RC receiver: DSMX Remote Receivers   

## Ground Control Station
ASUS Vivobook S14 (model number Q423S)


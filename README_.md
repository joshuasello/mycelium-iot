![mindstone logo](res/brand-panel-light.png)
# mindstone


## Basic Usage

#### Supported Platforms

|Platform               |Alias  |
|-----------------------|-------|
|Dummy (for testing)    |`dummy`|
|Raspberry Pi           |`rpi`  |
#### Supported Components
Components are instruments used by the driver that interface directly with the device.

### Creating a New Gate Network Controller
This controller is structurally organised as a network (or graph), storing modularised procedures in objects call gates. The way these gates are connected to each other determines the order in which the controller runs its procedures.

More generally, a controller is a directed graph where its nodes (the controller's gates) are unit operations that perform specific tasks. An edge (or connection) between two nodes represents the flow of data from one node to another. This makes it easy to define, represent, and implement different types of control systems that may suit different requirements.

##### Setting Up Supported Components

|Component          |Alias          |Setup Arguments                                                                |
|-------------------|---------------|-------------------------------------------------------------------------------|
|LED                |`led`          |`trigger_pin`                                                                  |
|Motor              |`motor`        |`trigger_pin`                                                                  |
|Servo              |`servo`        |`trigger_pin`,     |
|Switch             |`switch`       |`input_pin`                                                                    |
|Trigger            |`trigger`      |`trigger_pin`                                                                  |
|Ultrasonic Sensor  |`ultrasonic`   |`trigger_pin`, `echo_pin`, `trigger_pin=0.00001`                               |
##### Interfacing With Supported Components
|Component          |Writable Arguments                 |Readable Fields                    |
|-------------------|-----------------------------------|-----------------------------------|
|LED                |`is_on (bool)`, `toggle (bool)`    |`is_on (bool)`                     |
|Motor              |`is_on (bool)`, `toggle (bool)`    |`is_on (bool)`                     |
|Servo              |`angle (float)`, `is_acive (bool)` |`angle (float)`, `is_acive (bool)` |
|Switch             |None                               |`is_on (bool)`                     |
|Trigger            |`is_on (bool)`, `toggle (bool)`    |`is_on (bool)`                     |
|Ultrasonic Sensor  |None                               |`time_change (float)`              |


### Communication Types
|Connection Type    |Alias          |
|-------------------|---------------|
|TCP                |`tcp`          |
# CrowdPulse by Très tigré
![image](https://github.com/user-attachments/assets/a9d8b12e-539d-49e5-ac4c-3332414f2833)


# Project Overview
## Introduction
CrowdPulse is an innovative solution designed to measure and analyze audience engagement during live events, such as lectures, conferences, and presentations. By leveraging advanced AI-powered video analytics, CrowdPulse provides real-time insights into audience behavior, enabling speakers and organizers to optimize their events for maximum impact.

## Key Features
- **Real-Time Engagement Monitoring**: Tracks audience attention levels, detecting drops or spikes in engagement during the event.
- **Post-Event Analysis**: Offers detailed visualizations and statistics to analyze audience engagement over time.
- **VMS Integration**: Seamlessly integrates with Nx Witness VMS, enabling custom Event Rules, access to recorded video archives, and analytics metadata.
- **Cross-Platform Accessibility**: Provides a lightweight web application accessible via desktop, mobile browsers.

## Why CrowdPulse?
Unlike traditional methods, such as post-event surveys, CrowdPulse delivers actionable insights in real time, empowering organizers to make data-driven decisions. Whether it's enhancing speaker performance, improving content delivery, or boosting overall event satisfaction, CrowdPulse is the go-to tool for transforming audience engagement into measurable value.

## Target Audience
CrowdPulse is tailored for venue managers, event organizers, speakers, and educational institutions, helping them unlock the full potential of their audience data to improve outcomes and boost profitability.

# Techologies used
1. Having **NetworkOptix Open Source components** as a foundation of the Plugin allowed us to kickstart the development quickly. Open source components provide vast amount of libraries need to develop a plugin, without needing of any additional dependencies:
   - network library (network stack)
   - utils library (useful tools)
   - media library (codecs and stuff)
   - other
   Included ready to go smaple plugin and  CMake build system allows to start development right away.
2. Included in the Open Source Components, **Nx Kit** library provided a rich interface of the communication between server and plugin. 
3. **Nx AI Manager** allows easy and fast training, integration and deployment of the AI models.
4. Powerful Mediaserver **REST API** and its **documentaion** allowed to integrate more with the Nx ecosystem.   

# Demo Virtual Machine
We've prepaired pre-configured a demonstration VM that you can download [HERE](https://drive.google.com/file/d/1Vcr7yhv5MgFURlRo-QbKZ11uZLc69pRV/view?usp=sharing) (requires VirtualBox)

VM user: test
VM password: qweasd234

VMS user: admin
VMS password: qweasd234

# Build instructions
1. Download and unpack official [NetworkOptix open-source components](https://github.com/networkoptix/nx_open) code to `~/nx_open`
2. Install all needed prerequisites to build NetworkOptix open-source components
3. Download and unpack `crowdpulse_plugin` folder to `~/nx_open/vms/server/plugins/analytics/` folder
4. Execute the following command to add CrowdPulse plugin to CMake configuration:
  ```
  cd  ~/nx_open/vms/server/plugins/analytics
  echo "add_subdirectory(crowdpulse_plugin)" >> CMakeLists.txt
  ```
5. Execute the build script:
  ```
  cd  ~/nx_open/
  ./build.sh -DwithSdk=ON
  ```
  After the build succeeds, plugin shared library will be located at `~/nx_open-build/bin/bin/plugins_optional/libcrowdpulse_plugin.so`

# Installation Guide
## Preparation
1. Download and install [Nx Witness v6.0.2.40414 Client&Server](https://nxvms.com/download/releases/linux)
2. Download and install [Nx AI Manager](https://nx.docs.scailable.net/nx-ai-manager) according to the instructions on the page
3. Install python prerequisites from [requirements.txt](crowdpulse_plugin/static-resources/webapp/flask_app/requirements.txt) system-wide
4. Copy CrowdPulse shared library `libcrowdpulse_plugin.so` (built earlier) to the mediaserver's `plugins` folder (e.g. `/opt/networkoptix/mediaserver/bin/plugins`)
5. Setup the Server according to the instructions of the setup wizard in the Client

## Particular camera setup
1. Enable Nx AI Manager plugin for this camera and authorize it
2. Download and setup [CrowdPulse AI Model](https://drive.google.com/file/d/1RYXDlNtpqL0BcVVjsmxChhKLTWFEOi8S/view?usp=sharing) using the Nx AI Manager for this camera
3. Enable CrowdPulse plugin for this camera
4. Open the CrowdPulse WebApplication clicking on the link at the plugin's settings page and authorize with same login and password you used during the Server setup. 
5. Refresh settings of the CrowdPulse plugin. If everything is set up correctly, the corresponding message will be displayed

Right now authorization in Web Application have to be done once upon every server restart. You have not to redo authorization for every camera. 

# User Guide
## CrowdPulse Plugin
### General Settings
Using the Client you can access plugin's general settings on the tab **Plugins** of the **System Administration** dialog (can be opened using shortcut `Ctrl+Alt+A`). Select **CrowdPulse Plugin** in the list on the left.

![engine settings](https://github.com/user-attachments/assets/e301e8c8-853c-4cd0-9ccd-9505f500c9f4)

Here you can see the following settings:

| Caption  | Description | Default value |
| ------------- | ------------- | --- |
| Web Application HTTP Port  | Network port that will be used for the CrowdPulse Web Application server. If changed, Web Application restart (see below) is required. | 14200|
| Restart Web Application automatically | If checked, CrowdPulse Web Application server will be automatically restarted if case of failure or crash (that is totally unlikely, but just in case). | checked |
| Open | Use this button to open the CrowdPulse Web Application inside the Client | *(not applicable)* |
| Use proxy | If checked, CrowdPulse Web Application inside the Client will be proxied thru the Server. **WARNING: Due to the bug in the Server, proxying is not currently working as intended. Please use the Client on the same host with the Server** | checked |
| Stop | Stops the CrowdPulse Web Application server| *(not applicable)* |
| Restart | Stops and starts again the CrowdPulse Web Application server | *(not applicable)* |

### Ini file
Some advanced settings of the CrowdPulse Plugin can be configured using the `crowdpulse_plugin.ini` file.  Most of these settings are purposed to debug the Plugin and the WebApplication. 

**Warning: Any changes in this file without full understanding of the details can lead to breakage of the plugin or/and Web Application!** 

By default this configurational file is not present. To fill in the defaults, create dummy file (using e.g. `touch` command) in the `nx_ini` folder (located in e.g. `/home/networkoptix/.config/` path) and restart the server. Server will fill the file with all settings listed below and their default values.

In this configurational file you can see the following settings:
| Caption  | Description | Default value |
| ------------- | ------------- | --- |
|enableOutput| If enabled (set to `true`), greatly increases plugin's output to the Server's console and log. |false|
|disableUnpack| If enabled, CrowdPulse Plugin will not unpack WebApplication server resources on the Server statup|false|
|webAppExec|Executable to run the Web Application server|`python3`|
|webAppName|Web Application internal name|`flaskr`|
|restartDelay|Delay between Web Application server stop and subsequent restart if **Restart Web Application automatically** setting is checked, in seconds|1|

### Particular camera settings
In the client in the Camera settings dialog in the **Plugins** tab you can do some additional interation with the plugin.
Here you can check if basic setup is done right:
- if Nx AI Manager is not detected on the Server, corresponding warning banner will be displayed
- if you are not yet authorized in the CrowdPulse Web Application, corresponding warning banner will be displayed
- if both conditions are met, success banner will be displayed

Also on this page contains the link to the Web Application. 

Example of page with banner about missing Nx AI manager plugin:
![missing ai manager](https://github.com/user-attachments/assets/d41e4baf-0fda-4c35-b519-8990c947d03e)


### Analytics events
Currently CrowdPulse Plugin has 2 analytics events: 
- Engagement exceeds the target level
- Engagement is below target level

Rule setup:
![event rule](https://github.com/user-attachments/assets/588956ce-21a5-4570-b797-751b7d0920bb)

Event in the right panel:
![image (26)](https://github.com/user-attachments/assets/cd51ccbe-908b-4aad-b99f-420a780ded49)


These can be used to setup Event Rules. They are produced by the plugin if audience engagement exceeds the target level or fall below it.
More about target level you can read in [Web Applicaiton](#crowdpulse_web_application) section of this document.

### Analytics objects
CrowdPulse AI model produces 2 types of objects:
- **Attentive** - this person is considered attentive, will increase the overall engagement level
- **Distracted** - this person is considered distracted, will decrease the overall engagement level

Frames of the both object types are positioned on the persons' faces.

![objects](https://github.com/user-attachments/assets/e9999139-f5aa-43cd-af6a-3b4fff84b8f7)

### Web Application runtime data
In order to serve the Web Application, CrowdPulse plugin unpacks the HTTP-server runtime data to the location near `nx_ini` folder, in folder named `crowdpulse`.

If `nx_ini` is located on path `/home/networkoptix/.config/nx_ini`, then path will be `/home/networkoptix/.config/crowdpulse`.

**Please do not alter the files inside or change the access rights of this folder, this can lead to breakage of the plugin or/and Web Application!** 

## CrowdPulse Web Application
### Authorization
Unauthorized access to the Web Application is prohibited. 

If you try to open any Web Application page unauthorized, you will be redirected to the Log In page:
![login](https://github.com/user-attachments/assets/03b8f7f2-709f-406b-b756-edf915a0bdbb)

To log in use the credentatials you used during the server setup. You can log out from Web Application using the *Log out* button on the top of any page. 

If you don't want to use administrator account, you can create additional user in the **User Management** tab in **System Administration** dialog. This user shall have permissions to at least watch and receive metadata from cameras you want to use along with CrowdPulse Plugin. 

### Events
**Event** is the main entity around which the work with the application is built. It implies some kind of event such as a lecture, presentation, or speech.
Each event consists of the following:
- Name
- Start and End times
- Optional comment (description)
- Set of the cameras, that will be monitored and for which calculations will be made. Implied that all these cameras have CrowdPulse Plugin enabled and AI model set up using the Nx AI Manager.

You can edit this details or delete the Event anytime.

### Event list 
All Events are accesible in the list of the Events:
![event list](https://github.com/user-attachments/assets/5ba5f7ba-659a-49fe-8d55-fe9f27267462)

### Event creation
![event creation](https://github.com/user-attachments/assets/1e6252ec-ece3-4f3c-b5b8-47ce73f90baf)

### Event page
![изображение](https://github.com/user-attachments/assets/cf262704-5351-4b06-bbf4-c91abcef3adf)

On the Event page ypu can set the target audience engagement threshold in % and see the current dynamics.
Engagement grapgh is divided in the 3 zones:
- **Green**: Engagement is above than target level plus 10%
- **Yellow**: Engagement is around the target level, plus or minus 10%
- **Red**: Engagement is below than target level plus 10%

Graph is updated in real time.

Also, big icon in top left corner helps to quickly understand the current situation without reading the graph details. Icon color corresponds to the current engagement level.

Graph is calculated and shown for each camera in the Event separately. You can select the camera using the dropdown.

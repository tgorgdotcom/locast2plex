> **IMPORTANT FOR USERS RUNNING 0.2.x**: With the architectural changes in 0.3, a few config and set up tasks have changed. 


# locast2plex
A Python script and Docker image to connect locast to Plex's live tv/dvr feature. 

Uses ffmpeg, python, and a few awesome python modules to do most of the heavy lifting.  A lot of code was inspired from [telly](https://github.com/tellytv/telly) as well.


### FAIR WARNING/HEADS UP:
I won't have much time to troubleshoot and make changes to this script, so please understand if I am not able to address issues or pull requests.   I will try my best to help though!  

As always, pull requests are welcome.


## Set up options:
As of 0.3, are now two ways to use locast2plex -- either via a Docker container, or running as a command line/terminal program.  Both options are relatively straightforward, so which option you choose would probably be based on what you're more comfortable with and your current setup.


## Prerequisites
- Server ("always-on" computer) that is either network accessible to the Plex server, or running on the same server as Plex.  Make sure the server you choose is suitable for handling video.

- If you're using Docker, then make sure Docker is installed on the server. [See here for details on getting started with Docker](https://docs.docker.com/get-started/).

- If you choose to run this as a command line program, the following OSs and programs are required:
    - Windows (Mac and Linux probably work too, but this is untested)
    - Python 2.7.x
    - ffmpeg (if running under Mac or Linux)


- A locast account that you have donated to (non donated accounts have streams that terminate after 5-10 mins, so it won't work well for this setup).  Also be sure you are running the server from the same location that you want channels for.


## Some caveats
- As of now, EPG is provided solely through Plex.  Perhaps we can investigate getting EPG data through locast later, as the API supports it.


## Installation
1. Take note of the network accessible IP address of the server install you are using to create the container.  Note that the ports used are:
    - `6077` (tcp) for the hdhomerun device emulation service (and can be changed)
    - `1900` (udp) for SSDP discovery (which cannot be changed -- see troubleshooting for workarounds).

2. Choose your installation method:
    - **Via Docker:**  Set up the Docker container.  There are two options:
        1. Docker Compose:
            - Modify the `docker-compose.env` file to use the correct username, password, and the IP address (and port, if necessary) you took note of earlier.
            - Run `docker-compose up`

        2. Docker Command:
        
            Run the following command, making sure you modify the appropriate fields to match your configuration, with `external_addy` being the IP address you took note of earlier:
                
            `docker run -e username=username -e password=password -e external_addy=127.0.0.1 -p 6077:6077 -p 1900:1900/udp tgorg/locast2plex`

            If you are changing port `6077`, you will need to modify the port number in the first `-p` argument  AND add an `external_port` Docker environmental var, like so:

            `docker run -e username=username -e password=password -e external_addy=127.0.0.1 -e external_port=1234 -p 1234:6077 -p 1900:1900/udp tgorg/locast2plex`

    - **Via Terminal/Command Line**: Re-run the following command, replacing the username, password, and ip address to the correct values:
    
      `python main.py -u:username -p:password --debug --addy:127.0.0.1`

      If you need to change port `6077`, use the `--port` argument:
      
      `python main.py -u:username -p:password --debug --addy:127.0.0.1 --port:1234`


3. Configure Plex to use locast2plex: 
    - In the Plex settings on your server or web interface, select Live TV/DVR on the left-hand menu and add a device as you would normally add a HDHomeRun.  

    - You may need to enter the address manually as SSDP autodiscovery is buggy at the moment.  The address will be the value you set as the `external_addy` as well as the port (for example 127.0.0.1:6077).  

    - You may or may not see a box appear showing the recognized locast2plex instance, but even if this is not the case, you should be able to use the "Continue" button on the bottom right.

4. Configure your channels.  A few notes:
    - Make sure you have Plex using the proper "Broadcast" line up EPG for locast's broadcast location

    - Starting with 0.3, stations should have the correct channel and subchannel assignments now.  If there were any that were unrecognized, check the troubleshooting list below for assistance.



## Troubleshooting

### Incorrect channel numbers

Sometimes locast2plex will not be able to get the correct channel/subchannel number (perhaps an outdated number or a channel number from a similarly named station outside of the market).  Stations we don't recognize at all have their channel numbers assigned sequentially from 1000 on. 

For now, the easiest way to fix this is to find the correct channel id by research.  Usually searching the callsign via Google reveals the correct channel number (sometimes we'll see an updated callsign on a the first result as well).  Wikipedia is also extremely helpful here.

In the future, I'd like to implement some additional checks and tests for better channel recognition.  If you run into any problems, feel free to submit an issue so at least we can keep track of it.


### Working around port 1900

SSDP is used to *try* to enable Plex autodetection of the locast2plex instance, but it's currently buggy at the moment.  If you're using Docker, you can remove the `-p 1900:1900/udp` part of the docker command like so:

  `docker run -e username=username -e password=password -e external_addy=127.0.0.1 -p 6077:6077 tgorg/locast2plex`

For `docker-compose` users, delete the following line from `docker-compose.yml`:
    
  `- "1900:1900/udp"`
  
For now, there is no option for straight Python users to disable port 1900.  Let me know in github if this is an important option to implement.

### Submitting an issue

When submitting an issue, make sure to take note of the docker or command line output.  **Note that logs reveal username and approximate location information (in latitude/longitude as well as Locast's Nielsen market id), so be sure to look through what you post and clear out any data you want hidden before posting.**

> **IMPORTANT FOR USERS RUNNING 0.2.x**: With the architectural changes in 0.3, a few config and set up tasks have changed. 


# locast2plex
A Python script and Docker image to connect locast to Plex's live tv/dvr feature. 

Uses ffmpeg, python, and a few awesome python modules to do most of the heavy lifting


### FAIR WARNING/HEADS UP:
I won't have much time to troubleshoot and make changes to this script, so please understand if I am not able to address issues or pull requests.   I will try my best to help though!


## Set up options:
As of 0.3, are now two ways to use locast2plex -- either via a Docker container, or running as a command line/terminal program.  Both options are relatively straightforward, so which option you choose would probably be based on what you're more comfortable with and your current setup.


## Prerequisites
- Server ("always-on" computer) that is either network accessible to the Plex server, or running on the same server as Plex.  

- If you're using Docker, then make sure Docker is installed on the server. [See here for details on getting started with Docker](https://docs.docker.com/get-started/).

- If you choose to run this as a command line program, the following OSs and programs are required:
    - Windows (Mac and Linux probably work too, but this is untested)
    - Python 2.7.x
    - ffmpeg (if running under Mac or Linux)


- A locast account that you have donated to (non donated accounts have streams that terminate after 5-10 mins, so it won't work well for this setup).  Also be sure you are running the server from the same location that you want channels for.


## Some caveats
- As of now, EPG is provided solely through Plex.  Perhaps I can investigate getting EPG data through locast later, as the API supports it.


## Installation
1. Take note of the network accessible IP address of the server install you are using to create the container.  Note that the default port used is `6077`.  If there is another program/service using this port, you'll need to change the port in the following steps.

2. Choose your installation method:
    - **Via Docker:**  Set up the Docker container.  There are two options:
        1. Docker Compose:
            - Modify the `docker-compose.yml` file to use the correct username, password, and the IP address (and port, if necessary) you took note of earlier.
            - Run `docker-compose up`

        2. Docker Command:
        
            Run the following command, making sure you modify the appropriate fields to match your configuration, with `external_addy` being the IP address you took note of earlier:
                
            `docker run -e username=username -e password=password -e external_addy=127.0.0.1 -p 6077:6077 tgorg/locast2plex`

            If you are changing the port used, you will need to modify the port number here AND add an `external_port` Docker environmental var, like so:

            `docker run -e username=username -e password=password -e external_addy=127.0.0.1 -e external_port=1234 -p 1234:6077 tgorg/locast2plex`

    - **Via Terminal/Command Line**: Re-run the following command, replacing the username, password, and ip address to the correct values:
    
      `python main.py -u:username -p:password --debug --addy:127.0.0.1`

      If you need to change the port, use the `--port` argument:
      
      `python main.py -u:username -p:password --debug --addy:127.0.0.1 --port:1234`


3. Configure Plex to use locast2plex: 
    - In the Plex settings on your server or web interface, select Live TV/DVR on the left-hand menu and add a device as you would normally add a HDHomeRun.  

    - You must enter the address manually as autodetection will not work here.  The address will be the value you set as the `external_addy` as well as the port (for example 127.0.0.1:6077).  

    - You may or may not see a box appear showing the recognized locast2plex instance, but even if this is not the case, you should be able to use the "Continue" button on the bottom right.

4. Configure your channels.  A few notes:
    - Make sure you have Plex using the proper "Broadcast" line up EPG for locast's broadcast location

    - Starting with 0.3, stations should have the correct channel and subchannel assignments now.  If there were any that were unrecognized, check the troubleshooting list below for assistance.



## Troubleshooting

### Incorrect channel numbers

Sometimes locast2plex will not be able to get the correct channel/subchannel number; either a station will receive an outdated channel number, or (for stations we don't recognize at all) their channel numbers assigned sequentially from 1000 on. 

One thing you can try is to rerun a script I use to pull station information from the FCC.  It's `./fcc_facility/get_facilities.py`, and you can run it under python or in a Docker shell.  The resultant files `fcc_dma_markets_deduped.txt` and `tv_facilities.json` are created when the script complete.  Just copy the `tv_facilities.json` file to the root of the locast2plex folder and re-scan for channels in Plex.  If you are using docker, you will need to run the `get_facilities.py` script from the host, then recreate your container/image.
  

### Submitting an issue

When submitting an issue, make sure to take note of the docker or command line output.  
# locast2plex
A very simple docker image to connect locast to Plex's live tv/dvr feature. 

Uses telly, ffmpeg, the m3u8 python library, and docker to do most of the heavy lifting

### FAIR WARNING/HEADS UP:
I wont't have much time to troubleshoot and make changes to this script, so please understand if I am not able to address issues or pull requests.   I will try my best to help though!


## Prerequisites
- A Docker install that is network accessible to the Plex server.  In my case, I have Docker installed on the same computer as my Plex server

- A locast account that you have donated to (non donated accounts have streams that terminate after 5-10 mins, so it won't work well for this setup).  Also be sure you are running the server from the same location that you want channels for.


## Some caveats
- As of now, EPG is provided soley through Plex.  Perhaps I can investigate getting EPG data through locast later, as the API supports it.

- Channel listings are not accurate as the API doesn't actually give me a channel number.  You will probably need to manually map channels during the Plex set up process.  I'll keep sluthing to find a workaround, though...

## Getting Started
1. Take note of the IP address of the Docker install you are using to create the container

2. Set up the Docker container.  There are two options:
    1. Via Docker Compose:
        - Modify the docker-compose.yml file to use the correct username, password, and the IP address you took note of earlier.
        - Run `docker-compose up`

    2. Via Docker Command:
        - Run the following command, making sure you modifiy the appropriate fields to match your configuration, with listen_addy being the IP address you took note of earlier:
        
            `docker run -e username=username -e password=password -e listen_addy=127.0.0.1 -p 6077:6077 tgorg/locast2plex`

3. Configure Plex to use telly: 
    - In the Plex settings on your server or web interface, select Live TV/DVR on the lefthand menu and add a device as you would normally add a HDHomeRun.  
    - You must enter the address manually as autodetection will not work here.  The address will be the value you set as the `listen_addy` as well as the port (for example 127.0.0.1:6077).  
    - You may or may not see a box appear showing the recogized telly instance, but even if this is not the case, you should be able to use the "Continue" button on the bottom right.

4. Configure your channels.  A few notes:
    - Make sure you have Plex using the proper "Broadcast" line up EPG for locast's broadcast location
    - After Plex connects with telly, you will probably need to map channels manually (see why in caveats section above). 




## Troubleshooting
- Take note of the docker output.  If you see errors coming from telly, you may want to check the [telly wiki](https://github.com/tellytv/telly/wiki) to see if an answer is there

- If the errors are not coming from telly or if you're still running into issues, feel free to submit an issue
# locast2plex
A very simple docker image to connect locast to Plex's live tv/dvr feature. 

Uses telly, ffmpeg, the m3u8 python library, and docker to do most of the heavy lifting

### FAIR WARNING/HEADS UP:
I wont't have much time to troubleshoot and make changes to this script, so please understand if I am not able to address issues or pull requests.   I will try my best to help though!


## Prerequisites
- A Docker install that is network accessible to the Plex server.  In my case, I have Docker installed on the same computer as my Plex server

- A locast account that you have donated to (non donated accounts have streams that terminate after 5-10 mins, so it won't work well for this setup)


## Getting Started
1. Take note of the IP address of the Docker install you are using to create the container

2. Set up the Docker container.  There are two options:
    1. Via Docker Compose:
        - Modify the docker-compose.yml file to use the correct username, password, and IP.
        - Run `docker-compose up`

    2. Via Docker Command:
        - Run the following command, making sure you modifiy the appropriate fields to match your configuration:
        
            `docker run -e username=username -e password=password -e listen_addy=127.0.0.1 -p 6077:6077 tgorg/locast2plex`




## Troubleshooting
- Take note of the docker output.  If you see errors coming from telly, you may want to check the [telly wiki](https://github.com/tellytv/telly/wiki) to see if an answer is there

- If the errors are not coming from telly or if you're still running into issues, feel free to submit an issue
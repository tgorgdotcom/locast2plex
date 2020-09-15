# CHANGELOG

## 0.6.0 (unreleased)
 - Switch to Python 3 (Thanks @ratherDashing!)
 - Scripts are now fully linted (Thanks @deathbybandaid!)
 - Added all the market codes/FCC names so we don't have to add them when Locast enables them (Thanks @deathbybandaid!)

## 0.5.3
 - Updated Readme for spelling/clarity/credits (Thanks @tri-ler and @gogorichie!)
 - Added ability to place config in /app/config folder for Kubernetes users (Thanks @dcd!)
 - Added Detroit DMA support (Thanks @precision!)
 - Fix tuner count comparison (Thanks @ratherDashing!)
 - Refactored geolocation to mirror Locast methods (Thanks @FozzieBear!)
 - Added new contributing document and added unreleased section in changelog
 - Changed some var names for clarity.  
 - Fixed a bug where users running on bare command line/terminal could not set their ports. (Thanks @teconmoon)
 - Removed some old stuff in Dockerfile that are confusing users

## 0.5.2
 - Fixed a bug that prevented the success message from showing

## 0.5.1
 - Added success message at the end to indicate successful running
 - Fixed bug in docker-compose.yml
 - Updated readme for better clarity

## 0.5.0
 - Migrated environment settings to ini file -- should fix issues with special 
   characters in username/password, security concerns (thanks for the suggestion 
   @jcastilloalonso), as well as allowing to tweak internal settings without 
   resorting to modifying code.
 - Added ffmpeg.exe for Windows users
 - Merge fix to end ffmpeg zombie processes (thanks @FozzieBear!)
 - Add MINNEAPOLIS-ST. PAUL (thanks @steventwheeler!)
 - Fix for channel detection on subchannels ending in zero.

## 0.4.2
 - Enabled Miami and West Palm Beach markets
 - Fixed issue #10: renamed "docker-compose.env" to ".env"

## 0.4.1
- Added support for Tampa market
- Updated Changelog

## 0.4.0
- Fixed a bug in docker-compose.yml
- Fixed channels that only have one low resolution stream
- Overhauled channel detection and interpolation
- Reorganized api research notes to it's own folder

## 0.3.1
- Fix bugs in callsign detection
- More doc changes

## 0.3.0
- Created changelog!
- Remove telly dependency and doing the managing of streams and requests all by ourselves.
- Proper channel/subchannel applied to lineup

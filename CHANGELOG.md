# CHANGELOG
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

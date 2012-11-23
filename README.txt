PleXBMC - Use XBMC to play media from Plex Media Server

This is an XBMC addon that allows media and metadata stored in the Plex Media 
Server (PMS) to be viewed and played using XBMC.

INSTALLATION
------------

1. Download this zip file, placing it where is can be found by XBMC.
2. Install using "Install from zip file", which can be found in 
   Settings -right arrow-> Addons
or
   Settings -click-> Addons -> Install from Zip
   
3. Browse for the plugin zip file, select and install
4. If your PMS is installed on a seperate server, then configure the addon 
   with the IP address.

Go to Video -> Addon and you should be able to browse the PMS data structure 
and select the media you want to play

USING PLEXBMC
---------------
PleXBMC should work "out of the box" in most cases, as the default allows for automatic server discovery.
If this doesn't work, then discovery can be switched off, and a manually entered hostname or IP address can be used.

In addition, plexBMC can utilise myPlex to find remote and local servers.  To use myplex, simply type in your username and password.

PLAYING OPTIONS
---------------

PleXBMC will attempt to select the best play options for you:

1. PMS will first check if the file patch can be found locally.  This will use
   the same location as found on the PMS server.  So if the file is:
       /Volumes/media/path/to/file.mkv
   then the addon will use this path to find the file.
   
2. If the file cannot be found, then the addon will default to streaming via the
   PMS web server.  This does not transcode any file, and it will be played as
   normal.
   
You can override these by choosing either "http", "smb" or "AFP" in the "Stream from PMS"
setting.  "auto" is the default and will choose the best option.

PLAYING MEDIA LOCALLY
---------------------
If you want XBMC to make use of a local copy of the media (usually shared via SMB
or samba from a NAS) then you need to do *one* of the following:

1. Mount the PMS server filesystem on the client, so that they are available at all 
   times.  This is done outside of XBMC.

   or

2. Within XBMC, add the network filesystems as sources.  You do not need to set a
   content or scan these locations into the library - they simply need to be sources


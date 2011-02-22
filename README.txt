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

PLAYING OPTIONS
---------------
PMS will attempt to play the media based on the follow steps, which can be
overridden with the addon settings:

1. PMS will first check if the file patch can be found locally.  This will use
   the same location as found on the PMS server.  So if the file is:
       /Volumes/media/path/to/file.mkv
   then the addon will use this path to find the file.
   
2. If the file cannot be found, then the addon will default to streaming via the
   PMS web server.  This does not transcode any file, and it will be played as
   normal.
   
You can override these by choosing either "stream" or "smb" in the "Stream from PMS"
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

ADDON SETTINGS
--------------
Sorry, there are quite a few settings:
    * Plex Media Server Hostname - the IP/DNS name of the PMS server you want to contact
    * Is this a remote library (yes/no*)- are we connecting over the internet to the library
	* Stream from PMS (auto*,stream,smb) - select how you would like media to be played:
            auto - let the plugin decide between local and web server stream
            stream - all files to be played via web server stream
            smb - all files to be played from an smb share
    * Enable extra filter menus (yes/no*)- do you want the extra PMS menus (recently played, viewed, etc)
	* PMS Username/Password: - Required to contact remote library if security is enable in PMS
	* Enable transcoding (yes/no*)- You want to transcode all media for viewing
    * Transcode format (m3u8*, flv) - What format to use for transcoding
    
 * denotes default setting.  Not all options may be initially available and will depend on previous options
   
KNOWN LIMITATIONS
-----------------
1. You cannot play remote library (i.e. over internet) media if you have security set
   on PMS.  You can browse the structures and look at metadata, but playing will fail.  
   If you do not have a password set, then everything should be fine.
2. As above, but for transcoding.  This is a limitation in the XBMC playing model, but
   workarounds are being investigated.
3. PMS cannot stream (via the webserver or through transcoding) DVD and ISO media. This
   is a PMS limitation.  This can be overcome by mounted the media on the client and
   bypassing the stream from PMS web server.
4. Subtitles may not work.  Built-in subs should be fine, but subtitles which come as a
   seperate file will not play via PMS web server streaming.  If you need subs, then
   mount the media locally, bypassing the web server.  This is a PMS limitation.
5. XBMC cannot play PMS standard transcoded media (i.e. using m3u8 playlists). This 
   is being worked on by the XBMC team.
6. flv transcoding is experimental and may not work/crash PMS/bring about the end
   of time.  It's be fixed and tested as and when Plex supports it as an option.
7. Streaming of plugins may or may not work, depending on the type of plugin. Some 
   do (revision3 and TED) some don't (Apple trailers).

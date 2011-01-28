PleXBMC - Stream Plex Media server data into XBMC

This is an XBMC addon that allows media and metadata stored in the Plex Media 
Server (PMS) to be shared with XBMC.

INSTALLATION
------------

1. Download this zip file, placing it where is can be found by XBMC.
2. Install using "Install from zip file", which can be found in 
   Settings -> Addons
3. Browse for the plugin zip file, select and install
4. If your PMS is installed on a seperate server, then configure the addon 
   with this IP address.

Go to Video -> Addon and you shold be able to browse the PMS data structure 
and select the media you want to play

This will stream the file through the PMS server using http.  PMS will need
to remain running on the server during teh transfer

PLAYING LOCALLY
---------------
If you want the XBMC client to play this file locally, then you need to do 
two things:

1. Mount/share/make available the media files to the XBMC client.  This 
   should be done using SMB/samba, with the sources configured in XBMC 
   correctly.  You do not need to set a content or scan these locations into
   the library - they simply need to be sources
2. Configure the addon to use local media.  Simply select "Addon settings" 
   from the context menu and unselect the "Stream from PMS" option.
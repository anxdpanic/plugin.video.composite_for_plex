import urllib2
import xml.

class plexserver:

    def __init__(self, uuid=None, name=None, address=None, port=None, token=None, locality="local"):

        self.uuid=uuid
        self.name=name
        self.address=address
        self.port=port
        self.section_list=None
        self.token=token

    def get_details(self):

        return { 'uuid'    : self.uuid , 
                 'name'    : self.name ,
                 'address' : self.address ,
                 'port'    : self.port }

    def ping(self):
        url="/"
        
        if self._getXML(url):
            return True
                 
    def discover_sections (self):
        url="/library/sections"
        
        data = _getXML(url)
        
        tree = etree.fromstring(data).getiterator("Directory")
        temp_list=[]
        for sections in tree:
        
            section=plexsection(title = sections.get('title','Unknown').encode('utf-8') , 
                                type = sections.get('type','Unknown') ,
                                thumb = sections.gwet('thumb') ,
                                fanart = sections.get('art') ,
                                library = sections.get('key') ,
                                last_update = sectipons.get('lastUpdated') ,
                                uuid = section.get('uuid'))
                               
            self.section_list.append(section)
        
    def _getXML(self, url)

        url="http://%s:%s%s" % (self.address, self.port, url)
        request = urllib2.Request(url)
        if self.token:
            request.add_header('X-Plex-Token', self.token)
            
        response = request.urlopen(request)
        data = response.read()
        response.close()
        return data
    
        
class plexsection:

    def __init__(self, title=None, type=None, thumb=None, fanart=None, library=None, last_update=None, uuid=None):
    
        self.title=title
        self.type=type
        self.thumb=thumb
        self.fanart=fanart
        self.library=library
        self.last_update=update
        self.uuid=uuid
        
    def get_detals)self):
         
        return { 'title'        : self.title , 
                 'type'         : self.type ,
                 'thumb'        : self.thumb ,
                 'fanart'       : self.fanart ,
                 'library'      : self.library ,
                 'last_updated' : self.last_updated ,
                 'uuid'         : self.uuid }
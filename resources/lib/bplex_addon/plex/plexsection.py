class PlexSection:

    def __init__(self, data=None):

        self.title = None
        self.sectionuuid = None
        self.path = None
        self.key = None
        self.art = None
        self.type = None
        self.location = 'local'

        if data is not None:
            self.populate(data)

    def populate(self, data):

        path = data.get('key')
        if not path[0] == '/':
            path = '/library/sections/%s' % path

        self.title = data.get('title', 'Unknown').encode('utf-8')
        self.sectionuuid = data.get('uuid', '')
        self.path = path.encode('utf-8')
        self.key = data.get('key')
        self.art = data.get('art', '').encode('utf-8')
        self.type = data.get('type', '')

    def get_details(self):

        return {'title': self.title,
                'sectionuuid': self.sectionuuid,
                'path': self.path,
                'key': self.key,
                'location': self.location,
                'art': self.art,
                'type': self.type}

    def get_title(self):
        return self.title

    def get_uuid(self):
        return self.sectionuuid

    def get_path(self):
        return self.path

    def get_key(self):
        return self.key

    def get_art(self):
        return self.art

    def get_type(self):
        return self.type

    def is_show(self):
        if self.type == 'show':
            return True
        return False

    def is_movie(self):
        if self.type == 'movie':
            return True
        return False

    def is_artist(self):
        if self.type == 'artist':
            return True
        return False

    def is_photo(self):
        if self.type == 'photo':
            return True
        return False

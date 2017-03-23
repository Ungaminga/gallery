#!/usr/bin/env python
"""
gallery.py -- Generate an HTML gallery from a directory of jpg files.
Requires Python 3 or greater.
"""

#*****************************************************************************
#       Copyright (C) 2005 William Stein <was@math.harvard.edu>
#       Copyright (C) 2017 Ungaminga <loljkpro@cock.li>
#  (except for the exif reading code included near the middle of this file!)
#
#  Distributed under the terms of the GNU General Public License (GPL)
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    General Public License for more details.
#
#  The full text of the GPL is available at: http://www.gnu.org/licenses/
#*****************************************************************************

import pickle, os, random
from PIL import Image

PHOTO_EXTENSIONS=["jpg","jpeg", 'png']
PROPS = ['title']


class lazy_prop(object):
    def __init__(self, calculate_function):
        self._calculate = calculate_function
        self.__doc__ = calculate_function.__doc__

    def __get__(self, obj, _=None):
        if obj is None:
            return self
        value = self._calculate(obj)
        setattr(obj, self._calculate.__name__, value)
        return value

def prop(f):
    return property(f, None, None, f.__doc__)

class Photo(object):
    def __init__(self, filename, caption="", rating=0):
        self.__filename = filename
        self.caption = caption
        self.rating = rating
        self.size = (0, 0)
        self.thumb_size = (0, 0)

    def is_photo(self):
        return self.ext.lower() in PHOTO_EXTENSIONS

    @prop
    def filename(self):
        return self.__filename

    def ext(self):
        i = self.name.rfind(".")
        if i == -1:
            return ""
        return self.name[i+1:]

    @lazy_prop
    def base(self):
        i = self.name.rfind(".")
        if i == -1:
            return self.name
        return self.name[:i]

    @lazy_prop
    def path(self):
        return os.path.split(self.filename)[0]

    @lazy_prop
    def name(self):
        return os.path.split(self.filename)[1]

    def __lt__(self, other):
        """
        Compare based on filename.

        Date would be nice, but camera clocks are
        often wrong...
        
        """
        if not isinstance(other, Photo):
            return -1
        return self.filename < other.filename

    ########################################################
    ## Generate resized image of given size in given directory.
    ########################################################
    def small(self, size):
        dir = 'gallery/thumbs'
        if os.path.exists(dir) and not os.path.isdir(dir):
            os.remove(dir)
        if not os.path.exists(dir):
            os.mkdir(dir)
        file = "%s/%s-thumb.jpg"%(dir, self.base)
        
        im = Image.open(os.path.join(self.path, self.name))
        self.size = im.size
        if (im.size[0] > im.size[1]):
            im.resize((size, int(size*im.size[1]/im.size[0])), Image.ANTIALIAS).save(file)
            self.thumb_size = (size, int(size*im.size[1]/im.size[0]))
        else: 
            im.resize((int(size*im.size[0]/im.size[1]), size), Image.ANTIALIAS).save(file)
            self.thumb_size = int(size*im.size[0]/im.size[1]), size
        return file.replace("gallery/", "")

    ########################################################
    ## Generate HTML representation for this image in
    ## the directory dir, under os.curdir
    ########################################################
    def html(self, album, dir, prev, next, randoms, original=True):
        body = ""
        if self.size[0] < 600:
            body += '<link rel="prefetch" as="image" href="../%s/%s">\n' %(album.rel_dir, self.caption)
        body += '<H1><A href="../index.html">%s</A></H1>\n'%album.title
        body += '<A href="%s.html" title="Previous"><img src="thumbs/%s-thumb.jpg"></A>\n'%(prev.base, prev.base)
        body += '<A href="%s.html" title="Next"><IMG src="../%s/%s" width="%i"></A>\n'%(next.base, album.rel_dir, self.caption, self.size[0] )
        body += '<A href="%s.html" title="Next"><img src="thumbs/%s-thumb.jpg"></A>\n'%(next.base, next.base)
        body += '<br><a href="../%s/%s">%s</A>'%(album.rel_dir, self.name, self.name)
        body += '<a href="%s" download title="Download">&#8659;</a></li>\n'%(self.name)
        body += '(%ix%i)\n'%(self.size[0], self.size[1])
        body += '</div><!--id="page" -->\n<hr> '
        body += '<span> random pics: </span>\n'
        body += '<div style="overflow:hidden; max-height: 200px">'
        for image in randoms:
            body += '<A href="%s.html"><img src="thumbs/%s-thumb.jpg"></A>\n'%(image.base, image.base)
        body += '</div>'
        s = """<HTML>
        <HEAD>
           <TITLE>%s</TITLE>
           <link href="../style.css" rel="stylesheet" />
        </HEAD>
        <BODY>
            %s
           <div id="page">
           %s
        </BODY>
        </HTML>
        """%(self.name, generate_links(), body)
        
        open('%s/%s.html'%(dir, self.base), "w").write(s)


class Album(object):
    def __init__(self, photos=[], title="", rel_dir="", derived_from=None):
        """
        photos -- list of objects of type Photo
        title -- title of this album
        """
        self.__photos = list(photos)
        self.__photos.sort()   
        # photo_dict provides alternative dictionary access to the photos
        self.__create_photo_dict()
        self.title = title
        self.thumb_size = 200
        self.rel_dir = rel_dir
        if derived_from != None:
            for P in PROPS:
                if hasattr(derived_from, P) and P != 'title':
                    setattr(self, P, getattr(derived_from, P))


    def __create_photo_dict(self):
        self.__photo_dict = {}
        for F in self.__photos:
            self.__photo_dict[F.name.lower()] = F

    def __set_title(self, title):
        title=str(title)
        self.__title = title.replace("\n", " ")
    def __get_title(self):
        return self.__title
    title = property(__get_title, __set_title)

    def sort(self):
        """
        Sort by filename.
        """
        self.__photos.sort()
        self.__create_photo_dict()

    def __repr__(self):
        s="Album '%s' with %s photos:\n"%(self.title, len(self))
        for F in self:
            s += str(F) + "\n"
        return s

    def __len__(self):
        return len(self.__photos)

    def __getitem__(self, x):
        if isinstance(x, int):
            try:
                return self.__photos[x]
            except IndexError:
                raise IndexError("The index must satisfy 0 <= i < %s"%len(self))
        else:
            try:
                return self.__photo_dict[str(x).lower()]
            except KeyError:
                raise KeyError("No photo with name '%s'"%x)


    def _get_photos(self):
        """
        Return list of photos.
        """
        return self.__photos
    photos = property(_get_photos)

    def photo(self, name):
        try:
            return self.__photo_dict[name]
        except KeyError:
            raise KeyError("No photo named '%s' in the album."%name)

    def html(self, name="html", delete_old_dir=False):
        print("Generating gallery %s, %i total images: "%(self.title, len(self)))
        dir = os.curdir + "/" + name
        if os.path.exists(dir):
            if not delete_old_dir:
                raise IOError("The directory '%s' already exists.  Please delete it first."%dir)
        else:
            os.mkdir(dir)

        body = ""
        
        body += '<DIV>'

        for i in range(len(self)):
            P = self[i]
            base = P.base

            fname = P.small(self.thumb_size)
            
            if no_output == False:
                print("[%i from %i]: %s, size %ix%i"%(i, len(self), P.base, P.size[0], P.size[1]))
            else:
                progress = "%i from %i ["%((i+1), len(self))
                progress += "%-20s"%("="*((i+1)*20//len(self))) + "] %i%% done\r"%((i+1)*100//len(self))
                if i+1 == len(self):
                    progress += "\n"
                sys.stdout.write(progress)
                sys.stdout.flush()
            
            body += """
                <a href="%s.html" alt="%s">
                <img src="%s" width=%i height=%i" title="%s"></a>
                """%(base, P.caption, fname, P.thumb_size[0], P.thumb_size[1], P.caption)
            i_prev = i - 1
            if i_prev < 0:
                i_prev = len(self)-1
            i_next = i + 1
            if i_next >= len(self):
                i_next = 0
            
            random_images = []
            count = 0
            s__photos = list(self.__photos)
            random.shuffle(s__photos)
            for itr in s__photos:
                if itr == self[i_prev] or itr== self[i_next] or itr == self[i]:
                    continue
                random_images.append(itr)
                count = count + 1
                if count == 9:
                    break
            P.html(self, dir, self[i_prev], self[i_next], random_images)

        body += '</DIV>\n\n'

        # Assemble
        s = """
        <HTML>
            <HEAD>
                <TITLE>
                %s
                </TITLE>
                <link href="style.css" rel="stylesheet" />
            </HEAD>
            <BODY>
            %s
            <H1> %s</H1>
            %s
            </FONT>
            </BODY>
        </HTML>
        """%(self.title, generate_links(), self.title, body)

        open("%s/index.html"%dir,"w").write(s)


    def __add__(self, other):
        if not isinstance(other, Album):
            raise TypeError("other must be an Album.")
        photos = self.photos + other.photos
        title = self.title + " + " + other.title
        return Album(photos, title, other.rel_path, self)

    def save(self, filename):
        pickle.dump(self, open(filename,"w"))
    
    def max_count(self, count):
        count = int(count)
        return Album(self.__photos[:count], self.title, self.rel_dir, self)
    

def extension(file):
    i = file.rfind(".")
    if i == -1:
        return ""
    return file[i+1:]

def load_album(filename):
    return pickle.load(open(filename))

def save_album(album, filename):
    album.save(filename)

def album(dir, no_output):
    """
    Create an album from the files in a given directory.

    CAPTIONS, RATINGS, and FORMAT:

        If any text file (suffix .txt) is in the directory, this
        function extracts ratings, captions and other meta information
        from it.  The format of the file is the following:

           photo.jpg: 2 [This is a photo of a rainbow
           and a dog.]

           photo7.jpg: Tish William George

           video1.avi: 0 This is a video of a circus.

        The first entry is the name of one of the images (or videos)
        in the directory, followed by a colon.  Right after the name
        is a whole number, which is a rating for that, with bigger
        ratings being better.  The default rating is 0.  All text from
        there until the next image (or video, or end of file) is
        caption text.  The caption text is option and must be enclosed
        in square brackets if it spans more than one line.  The rating
        can also be optionally omitted, in which case it defaults to
        0.

    NOTES:
        * The caption text can be arbitrarily long and need not fit
          all on one line.  The caption text cannot contain brackets.

        * It's fine if there are entries in a txt file that don't
          correspond to actual files in the current directories.
          These are ignored.  This is allowed, since if you want to
          create a gallery from several directories, one way would be
          to copy some of the photos from each directory, then just
          concatenate the txt files.  That you have lots of extra
          entries in the notes.txt file won't cause a problem.

    INPUT:
        dir -- name of a directory
        
    OUTPUT:
        Album -- object of type album
    """
    rel_dir = dir
    dir = os.path.join(os.getcwd(),album_path)
    if not os.path.isdir(dir):
        raise IOError("No such directory: '%s'"%dir)
    i = dir.rfind("/")
    if i != -1:
        title = dir[i+1:]
    else:
        title = dir
    photos = []
    for F in os.listdir(dir):
        ext = extension(F).lower()
        if ext in PHOTO_EXTENSIONS:
            P = Photo(dir + "/" + F, caption=F)
            photos.append(P)
    A = Album(photos, title, rel_dir)
    A.no_output= no_output
    A.sort()

    return A


def write_css():
    css = """body {
    font-family: verdana, sans-serif;
    background: #555555;
    font: inherit;
    color: white;
}

a {
   color: lightblue;
}

a[download] {
   text-decoration: none;
}

h1 > a {
   position: absolute;
   left: 10px;
}

span {
      position: absolute;
      left: 10px;
      margin-top: -30px;
}
img {
     max-width: 30%;
}

#page{
      min-height: calc(100vh - 250px);
      text-align: center;
}
/* A div for links */
div.links{
    right:5px;
    position:absolute;
    background-color: khaki;
    border: green 2px solid;
    padding: 2px;
}

div.links > a{
      color: blue;
}
"""

    open("style.css", "w").write(css)

def generate_links():
    ret = ""
    if with_links == True and len(links):
        ret += '<div class="links">\n'
        for link in links:
            ret += '<a href="%s">%s</a><br>\n'%(link[0], link[1])
        ret += '</div>\n'
    return ret

##########################################################################


###############################################################
# What to do with album.py, when run as a shell script
###############################################################


if __name__ ==  '__main__':
    dir = "gallery"
    import sys
    argv = sys.argv
    if len(argv) == 1:
        prog = os.path.split(argv[0])[1]
        s =  "  ****************************************************************************\n"
        s += "  * HTML Gallery Program Version 2.0                                         *\n"
        s += "  * Copyright (C) 2005 William Stein <was@math.harvard.edu>                  *\n"
        s += "  * Copyright (C) 2017 Ungaminga <loljkpro@cock.li>                          *\n"
        s += "  * Distributed under the terms of the GNU General Public License (GPL)      *\n"
        s += "  ****************************************************************************\n"
        s += "\n"
        s += "  Usage: %s source_directory [files_count=0] ...\n"%(prog)
        s += "  If files_count == 0 - process whole directory. \n\n"
        s += "  Flags: \n"
        s += "   [--no-output]: Removes per-lane output thumbnail and html generating output\n"
        s += "   and enables progressbar.\n\n"
        s += "   [--with-links]: Adds links from your links list variable\n"
        s += "  The HTML gallery and thumbnails are stored in subdirectories\n"
        s += "  gallery and gallery/thumb.\n"
        s += "\n"*2
        open(".tmp_album","w").write(s)
        os.system("less .tmp_album")
        os.unlink(".tmp_album")

        sys.exit(0)

    album_path = ""
    count = 0
    no_output = False
    with_links = False
    links = [("https://github.com/Ungaminga/TES-L-Card-Images/archive/master.zip", "Download all")]
 
    for i in range(1, 5):
        if len(argv) > i:
            if argv[i] == "--no-output":
                no_output = True
                #print("no output setted")
                continue

            if (argv[i] == "--with-links"):
                with_links = True
                continue

            if album_path == "":
                album_path = str(argv[i])
                continue

            if count == 0:
                count = int(argv[i])
                
            
    write_css()
    a = album(album_path, no_output)
    if a.title == ".":
        a.title = os.path.split(os.path.abspath('.'))[1]
    t = a.title
    if (count): 
        a = a.max_count(count)
    
    a.title = t
    a.sort()  
    a.html(dir, delete_old_dir=True)
    index = open("%s/index.html"%dir).read()
    i = index.find("<a href=")
    x = index[i:]
    x = x.replace('href="', 'href="%s/'%dir)
    x = x.replace('src="', 'src="%s/'%dir)
    index = index[:i] + x
    open("index.html","w").write(index)
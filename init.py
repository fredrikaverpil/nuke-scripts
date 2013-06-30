import nuke, os, sys

# Make all filepaths load without errors regardless of OS (No Linux support and no C: support)
def myFilenameFilter(filename):
	if nuke.env['MACOS']:
		filename = filename.replace( 'X:', '/Volumes/Projects' )
		filename = filename.replace( 'Y:', '/Volumes/Assets' )
	if nuke.env['WIN32']:
		filename = filename.replace( '/Volumes/Projects', 'X:' )
		filename = filename.replace( '/Volumes/Assets', 'Y:' )

	return filename


# Use the filenameFilter(s)
nuke.addFilenameFilter(myFilenameFilter)


# Create OS specific variables (no Linux support)
volProjects = ''
volAssets = ''
if(sys.platform == 'win32'):
	volProjects = 'X:'
	volAssets = 'Y:'
elif(sys.platform == 'darwin'):
	volProjects = '/Volumes/Projects'
	volAssets = '/Volumes/Assets'


# Make these favorites show up in Nuke
nuke.addFavoriteDir('File server', volProjects + '/Projects/')
nuke.addFavoriteDir('Assets', volAssets)
nuke.addFavoriteDir('R&D', volProjects + '/RnD/')

# Formats
nuke.addFormat( '1024 576 PAL Widescreen' )
nuke.addFormat( '1280 720 HD 720p' )

# Set plugin/gizmo sub-folders
nuke.pluginAppendPath(volAssets + '/include/nuke/gizmos')
nuke.pluginAppendPath(volAssets + '/include/nuke/plugins')
nuke.pluginAppendPath(volAssets + '/include/nuke/scripts')
nuke.pluginAppendPath(volAssets + '/include/nuke/icons')

# Load Bokeh
os.environ['RLM_LICENSE'] = '5053@10.0.1.100'
if nuke.env['WIN32']:
	currentBokeh = 'Bokeh-Nuke6.3-1.2.1-win64'
if nuke.env['MACOS']:
	currentBokeh = 'Bokeh-Nuke6.3-1.2.1-Darwin'
nuke.pluginAppendPath(volAssets + '/include/nuke/plugins/bokeh/' + currentBokeh + '/')
nuke.load("pgBokeh")


# Check wheter OFX_PLUGIN_PATH has been set or not
try:
	os.environ['OFX_PLUGIN_PATH'] += ';'
except:
	os.environ['OFX_PLUGIN_PATH'] = ''
 
# Load Frischluft Lenscare
if(sys.platform == 'win32'):
	os.environ['OFX_PLUGIN_PATH'] += volAssets + '/bin/lenscare/lenscare_ofx_v1.44_win'
elif(sys.platform == 'darwin'):
	os.environ['OFX_PLUGIN_PATH'] += volAssets + '/bin/lenscare/lenscare_ofx_v1.44_osx'


# If Write dir does not exist, create it
def createWriteDir(): 
    file = nuke.filename(nuke.thisNode()) 
    dir = os.path.dirname( file ) 
    osdir = nuke.callbacks.filenameFilter( dir ) 
    try: 
        os.makedirs( osdir ) 
        return 
    except: 
        return

# Activate the createWriteDir function
nuke.addBeforeRender( createWriteDir )


# Make Write node default to sRGB color space
nuke.knobDefault('Write.mov.colorspace', 'sRGB')


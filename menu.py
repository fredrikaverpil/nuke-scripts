# -------- My Toolbar --------

# Initialize the toolbar menu
toolbar = nuke.toolbar('Nodes')

# My tools
toolbar.addCommand('My Nodes/Bezier', "nuke.createNode('Bezier')")
toolbar.addCommand( "My Nodes/pgBokeh", "nuke.createNode('pgBokeh')")


# -------- My File Menu --------

nuke.menu( 'Nuke' ).addCommand( 'My file menu/Rendering/Send to RenderManager', "nuke.load(\"submitNukeToRenderManager\"), submitNukeToRenderManager()" )
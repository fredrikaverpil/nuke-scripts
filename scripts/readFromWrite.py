"""readFromWrite
Read node generator v2.0, 2016-05-23

What's new in v2.0:
- Completely rewritten from scratch
- Improved detection of frame range
- Supports any padding format (not only %04d)
- Applies colorspace to Read node
- Supports not only Write nodes (see FILEPATH_KNOBS variable)
- Supports definition of "single file image sequence" formats
- PEP8 compliant!

Usage:
Select any Write node and run ReadFromWrite() after having sourced this
file, or put the following in your menu.py:

import readFromWrite
nuke.menu('Nuke').addCommand('Read from Write',
                             'readFromWrite.ReadFromWrite()',
                             'shift+r')
Please note:
Script is now started via ReadFromWrite() instead of the old
readfromWrite() function, so you'll have to update your scripts if you
are updating from a 1.x version.
"""

import os
import re
import glob

import nuke


# Settings
#
# knob names to use (from any node) as a base for Read node creation.
FILEPATH_KNOBS = ['file']
#
# This scripts needs to know whether to apply padding to a filepath
# or keep it without padding. Movie files should not have padding,
# for example. Add such "single file formats" here.
SINGLE_FILE_FORMATS = ['mov', 'mp4', 'mpeg4']


class ReadFromWrite(object):
    """Main class
    """
    def __init__(self):
        """Main function
        """
        super(ReadFromWrite, self).__init__()
        nodes = self.get_selected_valid_nodes()
        node_data = self.gather_node_data(nodes)
        self.create_read_nodes(node_data)

    def get_selected_valid_nodes(self):
        """Return list of nodes which should have Read nodes creaeted
        for them.
        """
        valid_nodes = []
        selected_nodes = nuke.selectedNodes()
        for node in selected_nodes:
            for k in FILEPATH_KNOBS:
                if not isinstance(node.knob(k), type(None)):
                    valid_nodes.append(node.name())  # contains allowed knob
        return valid_nodes

    def gather_node_data(self, nodes):
        """ Process the nodes and generate a dictionary of information
        which will be used to create the Read nodes.
        """
        data = {}
        for node in nodes:
            data[node] = {}
            for knob_name in FILEPATH_KNOBS:
                knob_value = nuke.toNode(node).knob(knob_name).getValue()
                knob_eval = nuke.toNode(node).knob(knob_name).evaluate()
                filepath = self.get_filepath(node, knob_value, knob_eval)
                if not isinstance(filepath, type(None)):
                    seq_info = self.frame_info(node, knob_value, knob_eval)
                    data[node][knob_name] = seq_info
        return data

    def combined_relative_filepath_exists(self, relative_filepath,
                                          return_filepath=False):
        """Combine the project directory with the filepath to get a
        existing filepath.
        If the option "return_filepath" is given, the combined
        filepath will get returned.
        """
        project_dir_value = nuke.root().knob('project_directory').getValue()
        if not os.path.exists(project_dir_value):
            project_dir = nuke.root().knob('project_directory').evaluate()
        filepath = os.path.join(project_dir, relative_filepath)
        filetype = filepath.split('.')[-1]
        frame_number = re.findall(r'\d+', filepath)[-1]
        basename = filepath[: filepath.rfind(frame_number)]
        filepath_glob = basename + '*' + filetype
        glob_search_results = glob.glob(filepath_glob)
        if len(glob_search_results) > 0:
            if return_filepath:
                return filepath
            else:
                return True
        else:
            if return_filepath:
                return None
            else:
                return False

    def get_filepath(self, node, knob_value, knob_eval):
        """Detect the filepath of a knob. Supports scripted
        and/or relative filepaths.
        """
        filepath = None
        if os.path.exists(knob_value):
            filepath = knob_value
        elif os.path.exists(knob_eval):
            filepath = knob_eval
        elif self.combined_relative_filepath_exists(knob_eval):
            filepath = self.combined_relative_filepath_exists(
                            knob_eval,
                            return_filepath=True)
        return filepath

    def frame_info(self, node, knob_value, knob_eval):
        """Returns all information required to create a Read node.
        """
        filepath = self.get_filepath(node, knob_value, knob_eval)
        current_frame = re.findall(r'\d+', filepath)[-1]
        padding = len(current_frame)
        basename = filepath[: filepath.rfind(current_frame)]
        filetype = filepath.split('.')[-1]
        firstframe = None
        lastframe = None

        # First and last frame from Read node
        if nuke.toNode(node).Class() == 'Read':
            firstframe = int(nuke.toNode(node).knob('first').getValue())
            lastframe = int(nuke.toNode(node).knob('last').getValue())

        # Check on disk for number of frames
        frames = []
        filepath_glob = basename + '*' + filetype
        glob_search_results = glob.glob(filepath_glob)
        for f in glob_search_results:
            frame = re.findall(r'\d+', f)[-1]
            frames.append(frame)
        frames = sorted(frames)

        # First and last frame from glob search
        if isinstance(firstframe, type(None)):
            firstframe = frames[0]
        if isinstance(lastframe, type(None)):
            lastframe = frames[len(frames)-1]
            if lastframe < 0:
                lastframe = firstframe

        # Filepath, depending on if it is a single file or if it is
        # a sequence
        if filetype in SINGLE_FILE_FORMATS:
            # Movie file
            filepath_processed = filepath
        else:
            # Image sequence
            filepath_processed = basename + '#'*padding + '.' + filetype

        # If filepath was relative, keep it that way
        if './' in filepath:
            filepath_processed = filepath_processed[filepath.rfind('./'):]

        # Color space
        colorspace = None
        if not isinstance(nuke.toNode(node).knob('colorspace'), type(None)):
            colorspace = nuke.toNode(node).knob('colorspace').getValue()

        # Premultiplied
        premultiplied = None
        if not isinstance(nuke.toNode(node).knob('premultiplied'), type(None)):
            premultiplied = nuke.toNode(node).knob('premultiplied').getValue()

        frame_data = {
                    'filepath': filepath_processed,
                    'firstframe': firstframe,
                    'lastframe': lastframe,
                    'colorspace': colorspace,
                    'premultiplied': premultiplied
                    }

        return frame_data

    def create_read_nodes(self, data):
        """Creates the Read node(s).
        """
        for node in data:
            for knob in data[node]:
                filepath = data[node][knob]['filepath']
                filetype = filepath.split('.')[-1]
                firstframe = int(data[node][knob]['firstframe'])
                lastframe = int(data[node][knob]['lastframe'])

                r = nuke.createNode('Read')

                if filetype in SINGLE_FILE_FORMATS:
                    # Movie file
                    r.knob(knob).fromUserText(filepath)
                else:
                    # Image sequence
                    r.knob(knob).setValue(filepath)
                    r.knob('first').setValue(firstframe)
                    r.knob('last').setValue(lastframe)

                if not isinstance(nuke.toNode(node).knob('colorspace'),
                                  type(None)):
                    colorspace = str(data[node][knob]['colorspace'])
                    r.knob('colorspace').setValue(colorspace)
                if not isinstance(nuke.toNode(node).knob('premultiplied'),
                                  type(None)):
                    premultiplied = str(data[node][knob]['premultiplied'])
                    r.knob('premultiplied').setValue(premultiplied)

            height = nuke.toNode(node).screenHeight()
            xpos = nuke.toNode(node).xpos()
            ypos = nuke.toNode(node).ypos()
            r.setXpos(xpos)
            r.setYpos(ypos + height + 20)

"""readFromWrite
Read node generator v2.1, 2016-05-25

Changelog:
- v2.1:
    - Fixed bug where Read node always got premultiplied
    - Support for ../ in filepath/expression
    - Dialog on "filepath not found" error
    - Set origfirst, origlast framerange
    - Additional movie file format support (see SINGLE_FILE_FORMATS
      variable)
    - General cleanup of various methods for greater maintainability
- v2.0:
    - Completely rewritten from scratch
    - Improved detection of frame range
    - Supports any padding format (not only %04d)
    - Applies colorspace to Read node
    - Supports not only Write nodes (see FILEPATH_KNOBS variable)
    - Supports definition of "single file image sequence" formats
      (see SINGLE_FILE_FORMATS variable)
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
# Knob names to use (from any node) as a base for Read node creation.
FILEPATH_KNOBS = ['file']
#
# This scripts needs to know whether to apply padding to a filepath
# or keep it without padding. Movie files should not have padding,
# for example. Add such "single file formats" here.
SINGLE_FILE_FORMATS = ['avi', 'mp4', 'mxf', 'mov', 'mpg', 'mpeg', 'wmv', 'm4v',
                       'm2v']


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
                    valid_nodes.append(node.name())
        return valid_nodes

    def gather_node_data(self, nodes):
        """Process the nodes and generate a dictionary of information
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

    def project_dir(self):
        """Return the project directory"""
        project_dir = nuke.root().knob('project_directory').getValue()
        if not os.path.exists(project_dir):
            project_dir = nuke.root().knob('project_directory').evaluate()
        return project_dir

    def combined_relative_filepath_exists(self, relative_filepath,
                                          return_filepath=False):
        """Combine the project directory with the filepath to get a
        valid and existing filepath.
        If the option "return_filepath" is given, the combined
        filepath will get returned.
        This scenario is hit when an expression is evaluated into a
        relative filepath.
        """
        project_dir = self.project_dir()
        filepath = os.path.abspath(os.path.join(project_dir,
                                   relative_filepath))
        filepath = filepath.replace('\\', '/')

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
        """Return a valid filepath or produce error"""
        filepath = None
        if os.path.exists(knob_value):
            filepath = knob_value
        elif os.path.exists(knob_eval):
            filepath = knob_eval
        elif not isinstance(self.project_dir(), type(None)) and \
                self.combined_relative_filepath_exists(knob_eval):
            filepath = self.combined_relative_filepath_exists(
                            knob_eval,
                            return_filepath=True)
        else:
            not_found = 'Filepath does not exist and/or cannot be' + \
                        'translated:\n' + knob_eval + \
                        '\n\nSkipping Read node creation based on ' + \
                        node + '.'
            nuke.message(not_found)

        return filepath

    def framerange_from_read(self, node):
        """Return the first and last frame from Read node"""
        firstframe = int(nuke.toNode(node).knob('first').getValue())
        lastframe = int(nuke.toNode(node).knob('last').getValue())
        return firstframe, lastframe

    def get_framerange(self, node, basename, filetype):
        """ Returns the firstframe and the lastframe"""
        if nuke.toNode(node).Class() == 'Read':
            # Get framerange from Read
            firstframe, lastframe = self.framerange_from_read(node)
        else:
            # Detect framerange
            frames = []
            filepath_glob = basename + '*' + filetype
            glob_search_results = glob.glob(filepath_glob)
            for f in glob_search_results:
                frame = re.findall(r'\d+', f)[-1]
                frames.append(frame)
            frames = sorted(frames)
            firstframe = frames[0]
            lastframe = frames[len(frames)-1]
        if lastframe < 0:
            lastframe = firstframe
        return firstframe, lastframe

    def determine_image_type(self, filepath, basename, padding, filetype):
        """Movie file or image sequence?"""
        if filetype in SINGLE_FILE_FORMATS:
            # Movie file
            filepath_img_determined = filepath
        else:
            # Image sequence
            filepath_img_determined = basename + '#'*padding + '.' + filetype
        return filepath_img_determined

    def determine_relativity(self, filepath):
        """Determine relativity for the generated filepath
        which is based on project directory compared with the filepath
        """
        filepath_relative = filepath
        project_dir = self.project_dir()
        if not isinstance(project_dir, type(None)):
            filepath_relative = filepath_relative.replace(project_dir, '.')
        return filepath_relative

    def process_filepath(self, filepath, filetype, basename, padding,
                         knob_value):
        """Generate the final filepath to be entered into the Read"""
        filepath_process = filepath
        filepath_process = self.determine_image_type(filepath_process,
                                                     basename,
                                                     padding,
                                                     filetype)
        filepath_process = self.determine_relativity(filepath_process)
        return filepath_process

    def get_knob_value(self, node, knob_name):
        """Return the value of a knob or return None if it is missing"""
        value = None
        if not isinstance(nuke.toNode(node).knob(knob_name), type(None)):
            value = nuke.toNode(node).knob(knob_name).getValue()
        return value

    def frame_info(self, node, knob_value, knob_eval):
        """Returns all information required to create a Read node.
        """
        filepath = self.get_filepath(node, knob_value, knob_eval)
        filepath = os.path.abspath(filepath)
        filepath = filepath.replace('\\', '/')
        current_frame = re.findall(r'\d+', filepath)[-1]
        padding = len(current_frame)
        basename = filepath[: filepath.rfind(current_frame)]
        filetype = filepath.split('.')[-1]
        firstframe, lastframe = self.get_framerange(node,
                                                    basename,
                                                    filetype)
        filepath_processed = self.process_filepath(filepath,
                                                   filetype,
                                                   basename,
                                                   padding,
                                                   knob_value)
        colorspace = self.get_knob_value(node, knob_name='colorspace')
        premultiplied = self.get_knob_value(node, knob_name='premultiplied')

        frame_data = {
                    'filepath': filepath_processed,
                    'firstframe': firstframe,
                    'lastframe': lastframe,
                    'colorspace': colorspace,
                    'premultiplied': premultiplied
                    }

        return frame_data

    def set_knob_from_data(self, node, data, knob, r, data_key):
        """Set data_key to knob of Read node r if not None"""
        if not isinstance(nuke.toNode(node).knob(data_key),
                          type(None)):
            value = int(data[node][knob][data_key])
            r.knob(data_key).setValue(value)

    def create_read_nodes(self, data):
        """Creates the Read node(s).
        """
        for node in data:
            for knob in data[node]:
                filepath = data[node][knob]['filepath']
                filetype = filepath.split('.')[-1]
                firstframe = int(data[node][knob]['firstframe'])
                lastframe = int(data[node][knob]['lastframe'])

                # Create Read node
                r = nuke.createNode('Read')

                if filetype in SINGLE_FILE_FORMATS:
                    # Movie file
                    r.knob(knob).fromUserText(filepath)
                else:
                    # Image sequence
                    r.knob(knob).setValue(filepath)
                    r.knob('first').setValue(firstframe)
                    r.knob('last').setValue(lastframe)
                    r.knob('origfirst').setValue(firstframe)
                    r.knob('origlast').setValue(lastframe)

                # Re-apply remaining knob values
                self.set_knob_from_data(node, data, knob, r,
                                        data_key='colorspace')
                self.set_knob_from_data(node, data, knob, r,
                                        data_key='premultiplied')

                # Read node placement
                height = nuke.toNode(node).screenHeight()
                xpos = nuke.toNode(node).xpos()
                ypos = nuke.toNode(node).ypos()
                r.setXpos(xpos)
                r.setYpos(ypos + height + 20)

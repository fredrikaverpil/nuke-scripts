"""readFromWrite
Read node generator v2.3, 2016-06-08

Changelog:
- v2.3:
    - Bug fix: crash when knob "use_limit" isn't available on node
    - Accidentally left ReadFromWrite() at bottom of script in v2.2
- v2.2:
    - Support for nodes with filepath which does not exist on disk
      (will read Write node settings or incoming framerange)
    - Support for additional Read/Write node option "raw"
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
                knob_value = self.get_knob_value(node, knob_name)
                knob_eval = nuke.toNode(node).knob(knob_name).evaluate()
                frame_info = self.frame_info(node, knob_value, knob_eval)
                data[node][knob_name] = frame_info
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

    def filepath_from_disk(self, node, knob_value, knob_eval):
        """Return a valid filepath or return None"""
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
        return filepath

    def framerange_from_read(self, node):
        """Return the first and last frame from Read node"""
        firstframe = int(self.get_knob_value(node, 'first'))
        lastframe = int(self.get_knob_value(node, 'last'))
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

    def node_options(self, node):
        """Return the values of selected node options"""
        colorspace = self.get_knob_value(node=node, knob_name='colorspace')
        premultiplied = self.get_knob_value(node=node,
                                            knob_name='premultiplied')
        raw = self.get_knob_value(node=node,
                                  knob_name='raw')
        options = {'colorspace': colorspace,
                   'premultiplied': premultiplied,
                   'raw': raw
                   }
        return options

    def frame_info(self, node, knob_value, knob_eval):
        """Returns all information required to create a Read node"""
        filepath = self.filepath_from_disk(node, knob_value, knob_eval)
        if isinstance(filepath, type(None)):
            not_found = 'Filepath does not exist and/or cannot be' + \
                        'translated:\n' + node + ': ' + knob_eval + \
                        '\n\nCreate Read node anyway and guess framerange?'
            if nuke.ask(not_found):
                limit_to_range = self.get_knob_value(node, 'use_limit')
                if (not isinstance(limit_to_range, type(None)) and
                        int(limit_to_range) == 1):
                    # Use explicit framerange set on Write node
                    firstframe = int(self.get_knob_value(node, 'first'))
                    lastframe = int(self.get_knob_value(node, 'last'))
                else:
                    # Look at the framerange coming into the Write node
                    firstframe = int(nuke.toNode(node).frameRange().first())
                    lastframe = int(nuke.toNode(node).frameRange().last())

                filepath_processed = self.determine_relativity(knob_eval)
                node_options = self.node_options(node)
                frame_data = {
                            'filepath': filepath_processed,
                            'firstframe': firstframe,
                            'lastframe': lastframe,
                            'node_options': node_options
                            }
                return frame_data

        else:
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
            node_options = self.node_options(node)
            frame_data = {
                        'filepath': filepath_processed,
                        'firstframe': firstframe,
                        'lastframe': lastframe,
                        'node_options': node_options
                        }
            return frame_data

    def set_knob_from_data(self, node, data, knob, r, data_key,
                           is_option=False):
        """Set data_key to knob of Read node r if not None"""
        if not isinstance(nuke.toNode(node).knob(data_key),
                          type(None)):
            if is_option:
                value = data[node][knob]['node_options'][data_key]
            else:
                value = data[node][knob][data_key]
            try:
                value = int(value)
            except ValueError:
                value = str(value)
            if not isinstance(value, type(None)):
                r.knob(data_key).setValue(value)

    def create_read_nodes(self, data):
        """Creates the Read node(s)"""
        for node in data:
            for knob in data[node]:
                if isinstance(data[node][knob], type(None)):
                    pass  # Skip Read node generation for this node
                else:
                    filepath = data[node][knob]['filepath']
                    filetype = filepath.split('.')[-1]
                    firstframe = int(data[node][knob]['firstframe'])
                    lastframe = int(data[node][knob]['lastframe'])
                    node_options = data[node][knob]['node_options']

                    # Create Read node
                    r = nuke.createNode('Read')

                    # Read node placement
                    height = nuke.toNode(node).screenHeight()
                    xpos = nuke.toNode(node).xpos()
                    ypos = nuke.toNode(node).ypos()
                    r.setXpos(xpos)
                    r.setYpos(ypos + height + 20)

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
                    for node_option in node_options:
                        self.set_knob_from_data(node, data, knob, r,
                                                data_key=node_option,
                                                is_option=True)

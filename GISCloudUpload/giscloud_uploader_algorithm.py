# -*- coding: utf-8 -*-

"""
/***************************************************************************
 GISCloudUpload
                                 A QGIS plugin
 Uploader to GIs cloud
                              -------------------
        begin                : 2015-11-23
        copyright            : (C) 2015 by Spatial Vision
        email                : michael.king@spatialvision.com.au
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = 'Spatial Vision'
__date__ = '2015-11-23'
__copyright__ = '(C) 2015 by Spatial Vision'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from glob import glob
import os.path

from PyQt4.QtCore import QSettings
from qgis.core import QgsVectorFileWriter

from processing.core.GeoAlgorithm import GeoAlgorithm
from processing.core.parameters import ParameterMultipleInput, ParameterString
from processing.core.ProcessingLog import ProcessingLog
from processing.core.outputs import OutputVector
from processing.tools import dataobjects, vector, system

import requests
import zipfile

class GISCloudUploadAlgorithm(GeoAlgorithm):
    """This is an example algorithm that takes a vector layer and
    creates a new one just with just those features of the input
    layer that are selected.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the GeoAlgorithm class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT_LAYER = 'INPUT_LAYER'
    API_KEY = 'API_KEY'
    OUTPUT_FOLDER = 'OUTPUT_FOLDER'
    MAP_NAME = "MAP_NAME"

    def defineCharacteristics(self):
        """Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # The name that the user will see in the toolbox
        self.name = 'GIS Cloud Uploader'

        # The branch of the toolbox under which the algorithm will appear
        self.group = 'Web'

        # We add the input vector layer. It can have any kind of geometry
        # It is a mandatory (not optional) one, hence the False argument
        self.addParameter(ParameterMultipleInput(
            self.INPUT_LAYER, # tool parameter to store the input under.
            self.tr('Vector layers to upload to GISCloud'), # name as it appears in the window
            ParameterMultipleInput.TYPE_VECTOR_ANY,  # Either raster or vector
            True  # Not optional
        ))

        # self.addParameter(ParameterMultipleInput(
        #     self.INPUT_LAYER, # tool parameter to store the input under.
        #     self.tr('Raster layers to upload to GISCloud'), # name as it appears in the window
        #     ParameterMultipleInput.TYPE_RASTER,  # Either raster or vector
        #     True  # Not optional
        # ))
        #
        # self.addParameter(ParameterMultipleInput(
        #     self.INPUT_LAYER, # tool parameter to store the input under.
        #     self.tr('Files to upload to GISCloud'), # name as it appears in the window
        #     ParameterMultipleInput.TYPE_FILE,  # Either raster or vector
        #     True  # Not optional
        # ))

        self.addParameter(ParameterString(
            self.API_KEY,
            "GISCloud API Key",
            default="62f961b31cbd0bc067cfa6f31a787826"
        ))

        self.addParameter(ParameterString(
            self.OUTPUT_FOLDER,
            "GISCloud output folder name",
            default="QGIS upload"
        ))

        # self.addParameter(ParameterString(
        #     self.MAP_NAME,
        #     "GISCloud output map name",
        #     default="Map",
        #     # True
        # ))

    def processAlgorithm(self, progress):
        """Here is where the processing itself takes place."""

        # The first thing to do is retrieve the values of the parameters
        # entered by the user

        # map_name = self.getParameterValue(self.MAP_NAME)
        input_filenames = self.getParameterValue(self.INPUT_LAYER).split(",")
        output_filename = self.getParameterValue(self.OUTPUT_FOLDER)
        api_key = self.getParameterValue(self.API_KEY)

        rest_endpoint = "https://api.giscloud.com/1/"
        headers = {
            "API-Version": 1,
            "API-Key": api_key,
        }

        # newmap_name = rest_endpoint + "maps/" + map_name
        storage_url = rest_endpoint + "storage/fs/" + output_filename

        # r = requests.post(newmap_name, headers=headers, files=z, verify=False)

        for path in input_filenames:

            zip_path = system.getTempFilename("zip")
            with zipfile.ZipFile(zip_path, "w") as z:
                for p in glob(os.path.splitext(path)[0] + ".*"):
                    ProcessingLog.addToLog(
                       ProcessingLog.LOG_INFO,
                       p
                    )
                    z.write(p, os.path.basename(p))

            ProcessingLog.addToLog(
                ProcessingLog.LOG_INFO,
                zip_path
            )


            z =  {'file': open(zip_path, 'rb')}
            r = requests.post(storage_url, headers=headers, files=z, verify=False)
            # r.status_code

            ProcessingLog.addToLog(
                ProcessingLog.LOG_INFO,
                "Uploaded {}".format(path)
            )

        ProcessingLog.addToLog(
            ProcessingLog.LOG_INFO,
            "Uploaded all datasets to the GIS Cloud folder " + output_filename
        )
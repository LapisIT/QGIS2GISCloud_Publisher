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
from itertools import chain

from qgis.core import QgsCoordinateTransform, QgsCoordinateReferenceSystem, QgsCsException, QgsRectangle

from processing.core.GeoAlgorithm import GeoAlgorithm
from processing.core.parameters import ParameterMultipleInput, ParameterString, ParameterBoolean
from processing.core.ProcessingConfig import ProcessingConfig
from processing.core.ProcessingLog import ProcessingLog
from processing.tools import dataobjects, system

import requests
import zipfile
import json

from giscloud_utils import GISCloudUtils


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

    INPUT_LAYER_VECTOR = 'INPUT_LAYER_VECTOR'
    INPUT_LAYER_RASTER = "INPUT_LAYER_RASTER"
    API_KEY = 'API_KEY'
    OUTPUT_FOLDER = 'OUTPUT_FOLDER'
    MAP_NAME = "MAP_NAME"
    CHOOSE_MAP = "CHOOSE_MAP"

    def getIcon(self):
        """Get the icon.
        """
        return GISCloudUtils.getIcon()

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
            self.INPUT_LAYER_VECTOR, # tool parameter to store the input under.
            self.tr('Vector layers to upload to GISCloud'), # name as it appears in the window
            ParameterMultipleInput.TYPE_VECTOR_ANY,  # Either raster or vector
            True  # Not optional
        ))

        self.addParameter(ParameterMultipleInput(
            self.INPUT_LAYER_RASTER, # tool parameter to store the input under.
            self.tr('Raster layers to upload to GISCloud'), # name as it appears in the window
            ParameterMultipleInput.TYPE_RASTER,  # Either raster or vector
            True  # Not optional
        ))

        self.addParameter(ParameterString(
            self.OUTPUT_FOLDER,
            "GISCloud output folder name",
            default="QGIS upload"
        ))

        self.addParameter(ParameterBoolean(
            self.CHOOSE_MAP,
            "Would you like to add the uploaded files to a new map?",
            default=False
        ))

        self.addParameter(ParameterString(
            self.MAP_NAME,
            "GISCloud output map name: Leave blank if you do not want to produce a new map with your uploaded layers",
            default="Map Project"
        ))

    def processAlgorithm(self, progress):
        """Here is where the processing itself takes place."""

        # The first thing to do is retrieve the values of the parameters
        # entered by the user

        api_key = ProcessingConfig.getSetting(GISCloudUtils.GISCloud_character)

        input_filenames = filter(
            self.check_extension,
            chain(
                (self.getParameterValue(self.INPUT_LAYER_VECTOR) or "").split(","),
                 (self.getParameterValue(self.INPUT_LAYER_RASTER) or "").split(",")
            )
        )
        output_filename = self.getParameterValue(self.OUTPUT_FOLDER)
        map_created = str(self.getParameterValue(self.CHOOSE_MAP))
        map_name = self.getParameterValue(self.MAP_NAME)
        rest_endpoint = "https://api.giscloud.com/1/"
        base_headers = {
            "API-Version": 1,
            "API-Key": api_key,
        }
        map_url = rest_endpoint + "maps.json"
        layer_url = rest_endpoint + "layers.json"
        storage_url = rest_endpoint + "storage/fs/" + output_filename

        if not input_filenames:
            ProcessingLog.addToLog(
                ProcessingLog.LOG_WARNING,
                "No valid datasets found to upload"
            )
            return

        if map_created == 'True':
            bounds = self.bounds(input_filenames)
            mid = self.create_map(map_url, base_headers, map_name, bounds)
        else:
            ProcessingLog.addToLog(
                ProcessingLog.LOG_INFO,
                "No map will be created, all files will be added to the file manager in" + output_filename)
            mid = None


        for path in input_filenames:
            self.upload_to_filemanager(storage_url, base_headers, path)
            if mid:
               self.add_layer_to_map(mid, path, output_filename, layer_url, base_headers)


        ProcessingLog.addToLog(
            ProcessingLog.LOG_INFO,
            "Uploaded all valid datasets to the GIS Cloud folder " + output_filename
        )


    def help(self):
        """
        Get the help documentation for this algorithm.
        :return: Help text is html from string, the help html
        :rtype: bool, str
        """
        help_data = open(os.path.join(
            os.path.dirname(__file__),
            "doc",
            "Publishing instructions.html"
        )).read()

        return True, help_data


    def upload_to_filemanager(self, storage_url, base_headers, path):

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

        z = {'file': open(zip_path, 'rb')}
        post = requests.post(storage_url, headers=base_headers, files=z, verify=False)
        ProcessingLog.addToLog(
            ProcessingLog.LOG_INFO,
            str(post.status_code)
        )
        post.raise_for_status()


        ProcessingLog.addToLog(
            ProcessingLog.LOG_INFO,
            "Uploaded {}".format(path)
        )


    def check_extension(self, path):
        filename, file_extension = os.path.splitext(path)
        if file_extension in (".shp", ".mif", ".mid", ".tab", ".kml", ".gpx", ".tif", ".tiff", ".sid", ".ecw", ".img", ".jp2",
                              ".jpg", ".gif", ".png", ".pdf", ".json", ".geojson"):
            return True
        else:
            if path:  # i.e. not an empty string
                ProcessingLog.addToLog(
                    ProcessingLog.LOG_WARNING,
                    "{} is not an accepted filetype".format(path)
                )
            return False

    def create_map(self, map_url, base_headers, map_name, bounds):

        headers = {
            "ContentType": "application/json"
        }
        headers.update(base_headers)

        map_data = {
            "name": map_name,
            "bounds": {
                "x_min": bounds[0],
                "x_max": bounds[1],
                "y_min": bounds[2],
                "y_max": bounds[3]
            },
            "description": "Description",
            "proj4": "+init=epsg:4326",
            "units": "degree"
            }
        map_post = requests.post(map_url, headers=base_headers, data=json.dumps(map_data), verify=False)

        mid = int(map_post.headers['Location'].split("/")[-1])
        ProcessingLog.addToLog(
            ProcessingLog.LOG_INFO,
            "mid %i" % mid)

        ProcessingLog.addToLog(
            ProcessingLog.LOG_INFO,
            map_name + " was successfully uploaded to your account"
                )

        return mid

    def bounds(self, input_filenames):

        layers = [
            dataobjects.getObjectFromUri(path)
            for path in input_filenames
        ]

        extent = None
        for layer in layers:
            if layer.type() == 0:
                transform = QgsCoordinateTransform(layer.crs(), QgsCoordinateReferenceSystem('EPSG:4326')) # WGS 84
                try:
                    layerExtent = transform.transform(layer.extent())
                except QgsCsException:
                    print "exception in transform layer srs"
                    layerExtent = QgsRectangle(-180, -90, 180, 90)
                if extent is None:
                    extent = layerExtent
                else:
                    extent.combineExtentWith(layerExtent)

        print layers
        return (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum())


    def add_layer_to_map(self, mid, path, output_filename, layer_url, base_headers):
        basename = os.path.basename(path)
        headers = {
            "ContentType": "application/json"
        }
        headers.update(base_headers)

        ProcessingLog.addToLog(
            ProcessingLog.LOG_INFO,
            headers)

        layer_data = {
            "mid":  mid,
            "name": basename,
            "type": "polygon",
            "source": json.dumps({
                "type": "file",
                "src": "/" + output_filename + "/" + basename,
                "name": basename
            })
        }
        layers_post = requests.post(layer_url, headers=base_headers, data=json.dumps(layer_data), verify=False)

        layers_post.raise_for_status()

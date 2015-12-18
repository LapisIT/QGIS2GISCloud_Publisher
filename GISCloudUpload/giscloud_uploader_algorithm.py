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

from PyQt4.QtCore import QSettings
from qgis.core import QgsVectorFileWriter

from processing.core.GeoAlgorithm import GeoAlgorithm
from processing.core.parameters import ParameterMultipleInput, ParameterString, ParameterBoolean
from processing.core.ProcessingLog import ProcessingLog
from processing.core.outputs import OutputVector
from processing.tools import dataobjects, vector, system

import requests
import zipfile
import json

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
            self.API_KEY,
            "GISCloud API Key",
            default="62f961b31cbd0bc067cfa6f31a787826"
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

        # map_name = self.getParameterValue(self.MAP_NAME)
        input_filenames = filter(
            self.check_extension,
            chain(
                (self.getParameterValue(self.INPUT_LAYER_VECTOR) or "").split(","),
                 (self.getParameterValue(self.INPUT_LAYER_RASTER) or "").split(",")
            )
        )

        output_filename = self.getParameterValue(self.OUTPUT_FOLDER)
        api_key = self.getParameterValue(self.API_KEY)

        rest_endpoint = "https://api.giscloud.com/1/"
        headers = {
            "API-Version": 1,
            "API-Key": api_key,
            # "Content-Type": "application/json"
        }

        storage_url = rest_endpoint + "storage/fs/" + output_filename

        if not input_filenames:
            ProcessingLog.addToLog(
                ProcessingLog.LOG_WARNING,
                "No valid datasets found to upload"
            )
            return


        mid = self.create_map()

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

            z = {'file': open(zip_path, 'rb')}
            r = requests.post(storage_url, headers=headers, files=z, verify=False)
            r.raise_for_status()

            self.add_layer_to_map(min, os.path.basename(path), output_filename)

            ProcessingLog.addToLog(
                ProcessingLog.LOG_INFO,
                "Uploaded {}".format(path)
            )

        # TODO: Call a function to generate a map...

        ProcessingLog.addToLog(
            ProcessingLog.LOG_INFO,
            "Uploaded all valid datasets to the GIS Cloud folder " + output_filename
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


    def bounds(self, layers):
        extent = None
        for layer in layers:
            if layer.type() == 0:
                transform = QgsCoordinateTransform(layer.crs(), QgsCoordinateReferenceSystem('EPSG:4326')) # WGS 84 / UTM zone 33N
                try:
                    layerExtent = transform.transform(layer.extent())
                except QgsCsException:
                    print "exception in transform layer srs"
                    layerExtent = QgsRectangle(-180, -90, 180, 90)
                if extent is None:
                    extent = layerExtent
                else:
                    extent.combineExtentWith(layerExtent)

        return (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum())

    def create_map(self):
        #TODO: Return the MID
        input_mapname = self.getParameterValue(self.MAP_NAME)
        rest_endpoint = "https://api.giscloud.com/1/"
        api_key = "62f961b31cbd0bc067cfa6f31a787826"
        headers = {
            "API-Version": 1,
            "API-Key": api_key,
            "Content-Type": "application/json"
            }
        map_url = rest_endpoint + "maps.json"

        (xmin, ymin, xmax, ymax) = self.bounds(layers)

        data = {
            "name": input_mapname,
            "bounds": {
            "xmin": xmin, #todo; etc
            "xmax":extent.xMaximum(),
            "ymin":extent.yMinimum(),
            "ymax":extent.yMaximum()
            },
            "description": "This is us testing things because the API isn't documented...",
            "proj4": "+init=epsg:4326",
            "units": "degree"
            }
        r = requests.post(map_url, headers=headers, data=json.dumps(data), verify=False)

        ProcessingLog.addToLog(
            ProcessingLog.LOG_INFO,
            input_mapname + " was successfully uploaded to your account"
                )


    def add_layer_to_map(self, mid, layer_name, upload_folder):
        #TODO Write the add layer code here
        pass

    # def symbologystyle(self):
    #     var viewer,
    #         mapId = 271800,
    #         pointLayerId = 754188,
    #         lineLayerId = 754189,
    #         polygonLayerId = 754190,
    #         $ = giscloud.exposeJQuery(),
    #         updating = $.Deferred().resolve(),
    #
    #
    #     pointStyle1 = [
    #     {
    #         visible: true,
    #         expression: "isnull(value)",
    #         url: null,
    #         galleryUrl: null,
    #         symbol: {
    #             border: "30,199,72",
    #             bw: "4",
    #             color: "36,255,58",
    #             size: "16",
    #             type: "circle",
    #     }],
    #     lineStyle1 = [
    #     {
    #         expression: "",
    #         visible: true,
    #         color: "102,153,204",
    #         width: "3",
    #         bordercolor: "0,102,204",
    #         borderwidth: "4",
    #     }],
    #     polygonStyle2 = [
    #     {
    #         visible: true,
    #         expression: "",
    #         color: "247,182,52",
    #         bordercolor: "255,242,61",
    #         borderwidth: "4",
    #         labelfield: "value",
    #         fontname: "Arial Black",
    #         fontsize: "18",
    #         fontcolor: "99,63,8",
    #         outline: "255,242,61"
    #     }];





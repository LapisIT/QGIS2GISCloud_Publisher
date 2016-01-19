# -*- coding: utf-8 -*-
"""
***************************************************************************
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
 ***************************************************************************
"""

from glob import glob
from itertools import chain
from functools import partial

from qgis.utils import iface
from qgis.core import (
    QgsCoordinateTransform, QgsCoordinateReferenceSystem,
    QgsCsException, QgsRectangle, QgsRasterLayer, QGis)
from processing.core.GeoAlgorithm import GeoAlgorithm
from processing.core.parameters import (
    ParameterMultipleInput, ParameterString,
    ParameterBoolean, ParameterExtent)
from processing.core.ProcessingConfig import ProcessingConfig
from processing.core.ProcessingLog import ProcessingLog
from processing.tools import system, dataobjects
from GISCloudUpload.giscloud_utils import GISCloudUtils
import os.path
import requests
import zipfile
import json

__author__ = 'Spatial Vision'
__date__ = '2015-11-23'
__copyright__ = '(C) 2015 by Spatial Vision'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


class GISCloudUploadAlgorithm(GeoAlgorithm):
    """
    The functional algorithm for uploading QGIS environment workspace layers
    to a GIS Cloud account.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT_LAYER_VECTOR = 'INPUT_LAYER_VECTOR'
    INPUT_LAYER_RASTER = "INPUT_LAYER_RASTER"
    OUTPUT_FOLDER = 'OUTPUT_FOLDER'
    MAP_NAME = "MAP_NAME"
    CHOOSE_MAP = "CHOOSE_MAP"
    MAP_EXTENT = "MAP_EXTENT"

    def getIcon(self):
        """
        Get the icon.
        """
        return GISCloudUtils.getIcon()

    def defineCharacteristics(self):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # The name that the user will see in the toolbox
        self.name = 'GIS Cloud Uploader'

        # The branch of the toolbox under which the algorithm will appear
        self.group = 'Web'

        # We add the input vector layer. It can have any kind of geometry
        # It is a mandatory (not optional) one, hence the False argument
        self.addParameter(ParameterMultipleInput(
            self.INPUT_LAYER_VECTOR,  # tool parameter to store the input under.
            self.tr('Vector layers to upload to GISCloud'),  # name as it appears in the window
            ParameterMultipleInput.TYPE_VECTOR_ANY,  # Either raster or vector
            True  # Not optional
        ))

        self.addParameter(ParameterMultipleInput(
            self.INPUT_LAYER_RASTER,  # tool parameter to store the input under.
            self.tr('Raster layers to upload to GISCloud'),  # name as it appears in the window
            ParameterMultipleInput.TYPE_RASTER,  # Either raster or vector
            True  # Not optional
        ))

        self.addParameter(ParameterString(
            self.OUTPUT_FOLDER,  # specify the name of the folder in which to
            # store the uploaded layers
            "GISCloud output folder name",
            default="QGIS upload"  # default value for the folder to be uploaded
        ))

        self.addParameter(ParameterBoolean(
            self.CHOOSE_MAP,  # determine if you want to upload the files to a new map
            "Would you like to add the uploaded files to a new map? \n"
            "*Leave empty if you do not want to produce a new map with "
            "your uploaded layers*",
            default=False  # default not to upload to a new map
        ))

        self.addParameter(ParameterString(
            self.MAP_NAME,  # specify the map name to upload the files into
            "GIS Cloud output map name",
            default="Map Project"  # default map name
        ))

        self.addParameter(ParameterExtent(  # specify the extent you wish the new map to have
            self.MAP_EXTENT, "Upload map extent"
        ))

    def processAlgorithm(self, progress):
        """
        Here is where the processing itself takes place.

        :param progress: Interface to the processing window
        :type progress: processing.gui.AlgorithmDialog.AlgorithmDialog
        """

        # The first thing to do is retrieve the values of the parameters
        # entered by the user
        # the api key is derived from the optional settings value entered
        api_key = ProcessingConfig.getSetting(GISCloudUtils.GISCloud_character)

        input_filenames = filter(
            partial(self.check_extension, progress=progress),  # Aliases a function to pre-define an argument
            chain(  # producing a list from the selected layers to upload
                (self.getParameterValue(self.INPUT_LAYER_VECTOR) or "").split(";"),
                (self.getParameterValue(self.INPUT_LAYER_RASTER) or "").split(";")
            )
        )

        progress.setInfo("Gathering layers")
        progress.setPercentage(0)

        output_filename = self.getParameterValue(self.OUTPUT_FOLDER)
        map_created = str(self.getParameterValue(self.CHOOSE_MAP))
        map_name = self.getParameterValue(self.MAP_NAME)
        rest_endpoint = "https://api.giscloud.com/1/"
        base_headers = {
            "API-Version": 1,
            "API-Key": api_key,
        }
        # details the rest endpoint urls for the map creation,
        # layer upload to map and the file for the layers to be uploaded to
        map_url = rest_endpoint + "maps.json"
        layer_url = rest_endpoint + "layers.json"
        storage_url = rest_endpoint + "storage/fs/" + output_filename

        #  This first check establishes if the user
        #  has entered anything for uploading and returns nothing
        if not input_filenames:
            ProcessingLog.addToLog(
                ProcessingLog.LOG_WARNING,
                "No valid datasets found to upload"
            )
            return
        # Assesses if the user has chooses to
        # create a new map with the upload
        if map_created == 'True':
            bounds = self.bounds()  # seeks to determine the extent of the map
            progress.setInfo("Creating empty map")
            mid = self.create_map(map_url, base_headers, map_name, bounds)  # Map ID
        else:
            # provides feedback on the options taken
            # by the user and where the data will appear
            ProcessingLog.addToLog(
                ProcessingLog.LOG_INFO,
                "No map will be created, all files will be added "
                "to the file manager in" + output_filename)
            mid = None
        # sends each of the selected files to be individually processed
        # and entered into the giscloud file manager folder
        progress.setInfo("Uploading files")
        for i, path in enumerate(input_filenames, 1):
            percent = float(i) / (len(input_filenames) + 1) * 100
            progress.setPercentage(int(percent))
            progress.setInfo("Uploading " + path)
            self.upload_to_filemanager(storage_url, base_headers, path)
            if mid:
                self.add_layer_to_map(mid, path, output_filename, layer_url, base_headers)
        # validation and information feedback on the success of the upload process
        progress.setPercentage(100)
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
        # this is contained in the root folder
        # GISCloudUpload/doc/Publishing instructions.html
        # help can be found on the right tab in the toolbox
        help_data = open(os.path.join(
            os.path.dirname(__file__),
            "doc",
            "Publishing_instructions.html"
        )).read()
        return True, help_data

    def upload_to_filemanager(self, storage_url, base_headers, path):
        """
        # Sequentially uploads each of the selected files to
        # the specified file name in GIS Clouds file manager
        :param storage_url:
        :param base_headers:
        :param path:
        :return:
        """
        # Extracts the basename of the file, collects all
        # associated file type extensions and zips the files for upload
        zip_path = system.getTempFilename("zip")
        with zipfile.ZipFile(zip_path, "w") as ziptofm:
            for pathname in glob(os.path.splitext(path)[0] + ".*"):
                ziptofm.write(pathname, os.path.basename(pathname))
        # read binary and post file with GIS Cloud REST API
        ziptofm = {'file': open(zip_path, 'rb')}
        post = requests.post(storage_url, headers=base_headers, files=ziptofm, verify=False)
        post.raise_for_status()
        # feedback on the uploaded datasets as well as the file extensions
        ProcessingLog.addToLog(
            ProcessingLog.LOG_INFO,
            "Uploaded {}".format(path)
        )

    def check_extension(self, path, progress):
        """
        Due to the wider range of the accepted file types
        by QGIS the file extensions are checked and
        given a boolean value for further processing if they are accepted by GIS Cloud

        :param path: Path to check if valid dataset
        :type path: str
        :param progress: Interface to the processing window
        :type progress: processing.gui.AlgorithmDialog.AlgorithmDialog
        :rtype: bool
        """
        filename, file_extension = os.path.splitext(path)
        if file_extension in (".shp", ".mif", ".mid", ".tab", ".kml", ".gpx",
                              ".tif", ".tiff", ".ecw", ".img", ".jp2",
                              ".jpg", ".png", ".pdf", ".json", ".geojson"):
            return True
        else:
            # progress.error(path + " is not compatible with GISCloud.")
            # provides feedback on the rejection of a filetype
            if path:  # i.e. not an empty string
                progress.error(path + " is not compatible with GISCloud.")
                ProcessingLog.addToLog(
                    ProcessingLog.LOG_WARNING,
                    "{} is not an accepted filetype".format(path)
                )
            return False

    def create_map(self, map_url, base_headers, map_name, bounds):
        """
        Creates a new map in GIS Cloud if the
        user has specified the need for one.
        :param map_url:
        :param base_headers:
        :param map_name:
        :param bounds: A QgsRectange object
        :return:
        """
        # Appends the contentType command to the headers
        headers = {
            "ContentType": "application/json"
        }
        headers.update(base_headers)
        # gathers the SRC bounds of the associated uploaded layers and
        # converts them into WGS 84 (EPSG:4326)
        map_data = {
            "name": map_name,
            "bounds": json.dumps({
                "xmin": bounds.xMinimum(),
                "xmax": bounds.xMaximum(),
                "ymin": bounds.yMinimum(),
                "ymax": bounds.yMaximum(),
            }),
            "description": "Description",
            "proj4": "+init=epsg:900913",
            "epsg": 900913,
            "copyright": "Spatial Vision"
            }
        # GIS Cloud REST command for generating a new map
        map_post = requests.post(map_url, headers=base_headers,
                                 data=json.dumps(map_data), verify=False)
        # Extracting the newly generated Map ID from the JSON
        # output for use in the upload_to_map layers REST endpoint
        mid = int(map_post.headers['Location'].split("/")[-1])
        ProcessingLog.addToLog(
            ProcessingLog.LOG_INFO,
            map_name + " was successfully uploaded to your account")
        return mid

    def bounds(self):
        """
        Function for recalculating the bounded extents of the
        layers as they are processed. Under construction
        :return:
        """
        # Requires refinement for raster manipulation of bounds
        selected_extent = unicode(self.getParameterValue(self.MAP_EXTENT)).split(',')

        xMin = float(selected_extent[0])
        xMax = float(selected_extent[1])
        yMin = float(selected_extent[2])
        yMax = float(selected_extent[3])
        extent = QgsRectangle(xMin, yMin, xMax, yMax)

        mapCRS = iface.mapCanvas().mapSettings().destinationCrs()
        transform = QgsCoordinateTransform(
            mapCRS,
            QgsCoordinateReferenceSystem('EPSG:3785')  # WGS84
            # QgsCoordinateReferenceSystem('EPSG:3785')  # Popular vis mercator
        )

        try:
            layer_extent = transform.transform(extent)
        except QgsCsException:
            ProcessingLog.addToLog(ProcessingLog.LOG_WARNING,
                                   "exception in transform layer srs")
            layer_extent = QgsRectangle(-180, -90, 180, 90)

        ProcessingLog.addToLog(ProcessingLog.LOG_INFO, layer_extent.toString())

        return layer_extent


    def get_layer_geomtype(self, uri):
        """
        Passed in the path that's generated by Processing, determine whether the layer is
        point, line, polygon or raster and return that.

        :param uri: The URI generated by the processing input
        :type uri: str
        :return: One of point, line, polygon, or raster
        :rtype: str
        """
        layer = dataobjects.getObjectFromUri(uri, False)

        if isinstance(layer, QgsRasterLayer):
            return "raster"

        geom_type = layer.geometryType()
        geom_const = {
            QGis.Point: "point",
            QGis.Line: "line",
            QGis.Polygon: "polygon"
        }
        try:
            return geom_const[geom_type]
        except KeyError:
            raise IOError("Geometry type of %s not supported" % uri)


    def add_layer_to_map(self, mid, path, output_filename, layer_url, base_headers):
        """
        Providing the uploaded layers sequentially to the recently made map
        Naming the uploaded layer in the map by the basename of the file
        :param mid:
        :param path:
        :param output_filename:
        :param layer_url:
        :param base_headers:        :return:

        """
        # Appending the necessary contentType to the REST API post
        basename = os.path.basename(path)

        geomtype = self.get_layer_geomtype(path)

        headers = {
            "ContentType": "application/json"
        }
        headers.update(base_headers)
        # Providing the base JSON format to upload the layers to the map
        layer_data = {
            "mid":  mid,
            "name": basename,
            "type": geomtype,
            "source": json.dumps({
                "type": "file",
                "src": "/" + output_filename + "/" + basename,
                "name": basename
            })}
        # The rest API call to upload the layers to the map
        layers_post = requests.post(layer_url, headers=base_headers,
                                    data=json.dumps(layer_data), verify=False)
        layers_post.raise_for_status()

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
 This script initializes the plugin, making it known to QGIS.
"""

__author__ = 'Spatial Vision'
__date__ = '2015-11-23'
__copyright__ = '(C) 2015 by Spatial Vision'


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load GISCloudUpload class from file GISCloudUpload.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .giscloud_uploader import GISCloudUploadPlugin
    return GISCloudUploadPlugin()

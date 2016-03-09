# QGIS2GISCloud_Publisher

GIS Cloud uploader for QGIS
This tool permits the upload of vector and raster datasets into a 
GIS Cloud account using an account API key. Layers can be produced 
and manipulated locally in a QGIS workspace and reproduced directly 
into the file manager of the selected GIS Cloud account.

Input parameters
Uploadable file types are limited to the extensions accepted by GIS Cloud:
Vector: .shp, .mif, .mid, .tab, .kml, .gpx,.json, .geojson
Raster: .tif, .tiff, .ecw, .img, .jp2, .jpg, .png, .pdf
*upload of one or more in any combination of file formats is permitted. 
The size of the upload is restricted by the storage space available in 
the GIS Cloud account.

Processing output messages

To review the output messages from the process click on the speech bubble 
in the bottom right of the QGIS window and navigate to the tab 'Processing'. 
This will provide a description of the success or failure of folder and map 
creation as well as file types uploaded.

API Key
This tool requires the user to enter a GIS Cloud API Key as an input 
parameter. In order to generate an API Key log into your GIS Cloud 
account, click in the top right hand corner drop down menu 
Hi*Your Name*>>My Account. In the pop up box navigate to the far 
right tab API Access>> Add Key. This will produce a new API key, 
copy this key and keep it safe.

To enter it into QGIS click on the tab Processing>>Options. 
Expand Providers>> GISCloud Uploader. Ensure the activate box is 
ticked, double click on the space below and paste in the GIS Cloud 
API Key. You will only need to do this once.

Vector Layers
Click on the button with the three dots to produce a pop out menu from 
which to choose the vector layers you wish to upload. This will allow 
you to select any or all of the vector layers which are in your current 
project Layers Panel (limited to the size of your GIS Cloud storage 
limit). The name of the layer will be transferred directly to the 
upload folder.

Raster Layers
Click on the button with the three dots to produce a pop out menu from
which to choose the raster layers you wish to upload. This will allow
you to select any or all of the raster layers which are in your current
project Layers Panel (limited to the size of your GIS Cloud storage
limit). The name of the layer will be transferred directly to the
upload folder.

GIS Cloud folder name
Enter a name for the folder the layers will be uploaded into. If a 
name isn't entered the default name will be QGIS upload - if this 
folder already exists or if the name entered is the same as one which 
exists the new layers will be appended into that folder.

Check-box for optional map creation
If you would like to create a new map project in which to enter the 
uploaded layers check this tick box.

GIS Cloud project map name
This will be the name for the new map/project in which the 
layers will be uploaded.

Upload map extent
Provide the map extent for the layers you are uploading. In order for 
the map properties to honour the QGIS canvas projections it is necessary 
to select a custom map extent from the canvas or to use the canvas extent. 
Allowing QGIS to automatically determine the extent from the uploaded 
layers results in unpredictable ymin and ymax values when rendered 
in GIS Cloud.

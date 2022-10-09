from genericpath import exists
import arcpy
import os
import ConversionUtils

wks = arcpy.env.scratchWorkspace
expr = "fixName(!Name!)"
codeblock = """def fixName(val):
                    return str(val).split('.')[0]"""

def getFileName(path):
    bname = os.path.basename(path).split('.')[0]
    for x in bname:
        if x == '-':
            bname = bname.replace('-','')
    return bname

def gpxtoPolygon(gpxFiles, name_desc_col, coord_sys, outputFeature,area_condition='',area_unit='', 
                    RasterAttachment_condition='',RasterFiles_Location=''):
    try:
        polygons={}
        gpxFiles = ConversionUtils.SplitMultiInputs(gpxFiles)
        for gpxfile in gpxFiles:
            arcpy.GPXtoFeatures_conversion(gpxfile, os.path.join(wks, '{}_points'.format(getFileName(gpxfile))))
            arcpy.Project_management(os.path.join(wks, '{}_points'.format(getFileName(gpxfile))),
                                        os.path.join(wks, '{}_points_proj'.format(getFileName(gpxfile))), coord_sys,
                                        '',arcpy.SpatialReference(4326))
            with arcpy.da.SearchCursor(os.path.join(wks, '{}_points_proj'.format(getFileName(gpxfile))),['Shape@XYZ',name_desc_col]) as sc:
                for row in sc:
                    if row[1] not in polygons.keys():
                        polygons[row[1]] = [[row[0][0],row[0][1]]]
                    else:
                        polygons[row[1]].append([row[0][0],row[0][1]])
            arcpy.Delete_management(os.path.join(wks, '{}_points'.format(getFileName(gpxfile))))
            arcpy.Delete_management(os.path.join(wks, '{}_points_proj'.format(getFileName(gpxfile))))
        arcpy.CreateFeatureclass_management(os.path.dirname(outputFeature), os.path.basename(outputFeature),'POLYGON','','','',coord_sys)
        arcpy.AddField_management(outputFeature, name_desc_col, 'TEXT')
        with arcpy.da.InsertCursor(outputFeature,['Shape@',name_desc_col]) as ic:
            for x in polygons:
                arr = arcpy.Array([arcpy.Point(*coord)for coord in polygons[x]])
                arr.append(arr[0])
                plot = arcpy.Polygon(arr, coord_sys)
                ic.insertRow((plot, x))
        if area_condition == 'true':
            #Process: Compute area of various polygons
            arcpy.SetProgressorLabel('Computing Area of{}.........'.format(os.path.basename(outputFeature)))
            areaHeader = 'Area_{}'.format(area_unit.capitalize())
            arcpy.AddField_management(outputFeature, areaHeader, 'DOUBLE')
            arcpy.CalculateField_management(outputFeature, areaHeader, '!shape.area@{}!'.format(area_unit.lower()),'PYTHON')

        if RasterAttachment_condition == 'ATTACHED':
            arcpy.SetProgressorLabel('Creating Raster Catalog')
            arcpy.CreateRasterCatalog_management(wks, 'RasterCatalog')

            arcpy.SetProgressorLabel('Copying Certificates to RasterCatalog......')
            arcpy.WorkspaceToRasterCatalog_management(RasterFiles_Location, os.path.join(wks, 'RasterCatalog'))

            arcpy.SetProgressorLabel('Adding Name field to RasterCatalog......')
            arcpy.AddField_management(os.path.join(wks, 'RasterCatalog'), 'Name_0', 'TEXT')

            arcpy.SetProgressorLabel('Calculating Name field to RasterCatalog......')
            arcpy.CalculateField_management(os.path.join(wks, 'RasterCatalog'), 'Name_0', expr, 'PYTHON', codeblock)

            arcpy.SetProgressorLabel('Joining Certificates to {}......'.format(os.path.basename(outputFeature)))
            arcpy.JoinField_management(outputFeature, name_desc_col, os.path.join(wks, 'RasterCatalog'), 'Name_0')
            arcpy.DeleteField_management(outputFeature, 'Name_1')
            arcpy.DeleteField_management(outputFeature, 'Name_0')
            
            arcpy.Delete_management(os.path.join(wks, 'RasterCatalog'))
        pass
    except arcpy.ExecuteError as err:
        arcpy.AddError(err)
        for gpxfile in gpxFiles:
               if (exists(os.path.join(wks, '{}_points'.format(getFileName(gpxfile))))):
                arcpy.Delete_management(os.path.join(wks, '{}_points'.format(getFileName(gpxfile))))
               if (exists(os.path.join(wks, '{}_points_proj'.format(getFileName(gpxfile))))):
                arcpy.Delete_management(os.path.join(wks, '{}_points_proj'.format(getFileName(gpxfile))))
    finally:
        del(polygons) #clean up

if __name__=='__main__':
    args = tuple(arcpy.GetParameterAsText(i)for i in range(arcpy.GetArgumentCount()))
    gpxtoPolygon(*args)

from genericpath import exists
import arcpy
import os
import ConversionUtils

def wks(path):
    return os.path.dirname(path)

def Feat_shp(path):
    return '.shp' if os.path.basename(path).endswith('.shp') else ''


expr = "fixName(!Name!)"

codeblock = """def fixName(val):
                    return str(val).split('.')[0]"""

def getFileName(path):
    bname = os.path.basename(path).split('.')[0]
    for x in bname:
        if x == '-':
            bname = bname.replace('-','')
    return bname

def cleanUp(feature):
    arcpy.Delete_management(feature)

def attachRasterFiles(Raster_Files_Location, Feature_name_desc_col, Feature):
    arcpy.SetProgressorLabel('Creating Raster Catalog.......')
    arcpy.AddMessage('Creating Raster Catalog.......')
    arcpy.CreateRasterCatalog_management(wks(Feature), 'CatLog')

    arcpy.SetProgressorLabel('Copying Certificates to RasterCatalog......')
    arcpy.WorkspaceToRasterCatalog_management(Raster_Files_Location, os.path.join(wks(Feature), 'CatLog'))

    arcpy.SetProgressorLabel('Adding Name field to RasterCatalog......')
    arcpy.AddField_management(os.path.join(wks(Feature), 'CatLog'), 'Name_0', 'TEXT')

    arcpy.SetProgressorLabel('Calculating Name field to RasterCatalog......')
    arcpy.CalculateField_management(os.path.join(wks(Feature), 'CatLog'), 'Name_0', expr, 'PYTHON', codeblock)

    arcpy.SetProgressorLabel('Attaching Certificates to {}......'.format(os.path.basename(Feature)))
    arcpy.AddMessage('Attaching Certificates to {}......'.format(os.path.basename(Feature)))
    arcpy.JoinField_management(Feature, Feature_name_desc_col, os.path.join(wks(Feature), 'CatLog'), 'Name_0')
    arcpy.DeleteField_management(Feature, 'Name_1')
    arcpy.DeleteField_management(Feature, 'Name_0')
    arcpy.Delete_management(os.path.join(wks(Feature), 'CatLog'))

def gpxtoPolygon(gpxFiles, name_desc_col, coord_sys, outputFeature,area_condition='',area_unit='', 
                    RasterAttachment_condition='',RasterFiles_Location=''):
    try:
        polygons={}
        gpxFiles = ConversionUtils.SplitMultiInputs(gpxFiles)
        for gpxfile in gpxFiles:
            arcpy.GPXtoFeatures_conversion(gpxfile, os.path.join(wks(outputFeature), 
                                        '{}_points{}'.format(getFileName(gpxfile),Feat_shp(outputFeature))))

            arcpy.Project_management(os.path.join(wks(outputFeature),'{}_points{}'.format(getFileName(gpxfile),Feat_shp(outputFeature))),
                                        os.path.join(wks(outputFeature), '{}_points_proj{}'.format(getFileName(gpxfile),Feat_shp(outputFeature))),
                                        coord_sys,
                                        '',arcpy.SpatialReference(4326))

            with arcpy.da.SearchCursor(os.path.join(wks(outputFeature), '{}_points_proj{}'.format(getFileName(gpxfile),Feat_shp(outputFeature))),
                                        ['Shape@XYZ',name_desc_col]) as sc:
                for row in sc:
                    if row[1] not in polygons.keys():
                        polygons[row[1]] = [[row[0][0],row[0][1]]]
                    else:
                        polygons[row[1]].append([row[0][0],row[0][1]])
            cleanUp(os.path.join(wks(outputFeature), '{}_points{}'.format(getFileName(gpxfile),Feat_shp(outputFeature))))
            cleanUp(os.path.join(wks(outputFeature), '{}_points_proj{}'.format(getFileName(gpxfile),Feat_shp(outputFeature))))
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
            arcpy.AddMessage('Computing Area of{}.........'.format(os.path.basename(outputFeature)))
            areaHeader = 'Area_{}'.format(area_unit.capitalize())
            if len(areaHeader) > 10:
                areaHeader = areaHeader[0:10]
            arcpy.AddField_management(outputFeature, areaHeader, 'DOUBLE')
            arcpy.CalculateField_management(outputFeature, areaHeader, '!shape.area@{}!'.format(area_unit.lower()),'PYTHON')

        if RasterAttachment_condition == 'ATTACHED':
            attachRasterFiles(Raster_Files_Location=RasterFiles_Location, Feature_name_desc_col=name_desc_col, Feature=outputFeature)
        pass
    except arcpy.ExecuteError as err:
        arcpy.AddError(err)
        for gpxfile in gpxFiles:
               if (exists(os.path.join(wks(outputFeature),'{}_points{}'.format(getFileName(gpxfile),Feat_shp(outputFeature))))):
                arcpy.Delete_management(os.path.join(wks(outputFeature),'{}_points{}'.format(getFileName(gpxfile),Feat_shp(outputFeature))))
               if (exists(os.path.join(wks(outputFeature),'{}_points_proj{}'.format(getFileName(gpxfile),Feat_shp(outputFeature))))):
                arcpy.Delete_management(os.path.join(wks(outputFeature),'{}_points_proj{}'.format(getFileName(gpxfile),Feat_shp(outputFeature))))
    finally:
        arcpy.AddMessage('Cleaning up.................')
        del(polygons) #clean up

if __name__=='__main__':
    args = tuple(arcpy.GetParameterAsText(i)for i in range(arcpy.GetArgumentCount()))
    gpxtoPolygon(*args)
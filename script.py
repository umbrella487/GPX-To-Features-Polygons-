import arcpy
import os
import ConversionUtils

def fName(path):
    bname = os.path.basename(path).split('.')[0]
    for x in bname:
        if x in ['-','&']:
            bname = bname.replace(x,'_')
    return bname

def cleanUp(feature):
    arcpy.Delete_management(feature)

def gpxtoPolygon(gpxFiles, name_desc_col, outputFeature, computeArea='', areaUnit=''):
    try:
        polygons={}
        gpxFiles = ConversionUtils.SplitMultiInputs(gpxFiles)
        for gpxfile in gpxFiles:
            arcpy.GPXtoFeatures_conversion(gpxfile, r'in_memory\tempFile{}'.format(fName(gpxfile)))
            with arcpy.da.SearchCursor(r'in_memory\tempFile{}'.format(fName(gpxfile)),['Shape@XYZ',name_desc_col]) as sc:
                for row in sc:
                    if row[1] not in polygons.keys():
                        polygons[row[1]] = arcpy.Array(arcpy.Point(row[0][0],row[0][1]))
                    else:
                        polygons[row[1]].append(arcpy.Point(row[0][0],row[0][1]))
            cleanUp(r'in_memory\tempFile{}'.format(fName(gpxfile)))

        arcpy.CreateFeatureclass_management(os.path.dirname(outputFeature), os.path.basename(outputFeature),'POLYGON','','','',arcpy.SpatialReference(4326))
        arcpy.AddField_management(outputFeature, name_desc_col, 'TEXT')
        with arcpy.da.InsertCursor(outputFeature,['Shape@',name_desc_col]) as ic:
            for key,value in polygons.items():
                plot = arcpy.Polygon(value, arcpy.SpatialReference(4326))
                ic.insertRow((plot, key))

        if computeArea == 'true':
            fieldName = 'Area_'
            count = 0
            while len(fieldName) != 10:
                fieldName+=areaUnit[count]
                count+=1
            arcpy.AddField_management(outputFeature, fieldName, 'DOUBLE')
            arcpy.CalculateField_management(outputFeature, fieldName, '!shape.area@{}!'.format(areaUnit.lower()),'PYTHON')

    except arcpy.ExecuteError as err:
        arcpy.AddError(err)
        try:
            if arcpy.Exists(r'in_memory\tempFile{}'.format(fName(gpxfile))):
                arcpy.Delete_management(r'in_memory\tempFile{}'.format(fName(gpxfile)))
        except arcpy.ExecuteError as err2:
            arcpy.AddError(err2)
    finally:
        arcpy.AddMessage('Cleaning up.................')
        del(polygons) #clean up

if __name__=='__main__':
    args = tuple(arcpy.GetParameterAsText(i)for i in range(arcpy.GetArgumentCount()))
    gpxtoPolygon(*args)
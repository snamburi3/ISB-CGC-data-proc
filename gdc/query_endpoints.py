import json
import requests
import sys
import uuid

## -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

## Note: can get a nice mapping from the endpoint like this:
##       curl 'https://gdc-api.nci.nih.gov/cases/_mapping'
##
##  cases_fields:  aliquot_ids analyte_ids case_id created_datetime portion_ids
##                 sample_ids slide_ids state submitter_aliquot_ids submitter_analyte_ids
##                 submitter_id submitter_portion_ids submitter_sample_ids updated_datetime 
## 
##  files_fields:  access acl created_datetime data_category data_format data_type
##                 error_type experimental_strategy file_id file_name file_size file_state
##                 md5sum platform state state_comment submitter_id tags type updated_datetime 
##
## -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

cases_fields = []
files_fields = []

## -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

def get_all_case_ids ( cases_endpt ):

    print " "
    print " >>> in get_all_case_ids ... ", cases_endpt
    print " "

    maxSize = 1000
    ## maxSize = 10
    fromStart = 1
    done = 0 

    caseID_map = {}

    while not done:

        params = { 'fields': 'submitter_id,case_id', 
                   'sort': 'case_id:asc',
                   'from': fromStart, 
                   'size': maxSize }

        ## print " get request ", cases_endpt, params
        response = requests.get ( cases_endpt, params=params )
        rj = response.json()
        ## print json.dumps ( rj, indent=4 )

        ## expecting something like this in each rj['data']['hits']:
        ##    {
        ##        "case_id": "5bc515c8-7727-4d69-98e9-31bbcb748550",
        ##        "submitter_id": "TCGA-GN-A26A"
        ##    }

        try:

            iCount = rj['data']['pagination']['count']
            iFrom  = rj['data']['pagination']['from']
            iPages = rj['data']['pagination']['pages']
            iTotal = rj['data']['pagination']['total']
            iSize  = rj['data']['pagination']['size']
            ## print iCount, iFrom, iPages, iTotal, iSize

            fromStart += iCount
            if ( iCount == 0 ):
                ## print " got nothing back ... (?) "
                done = 1

            for ii in range(iCount):
                ## print ii, rj['data']['hits'][ii]
                case_id = rj['data']['hits'][ii]['case_id']
                submitter_id = rj['data']['hits'][ii]['submitter_id']
                ## print case_id, submitter_id
                if ( case_id not in caseID_map ):
                    caseID_map[case_id] = submitter_id
                else:
                    print " already have this one in dict ?!?! ", ii, iCount, case_id, submitter_id

            print "         ", len(caseID_map)

        except:
            done = 1

        ## temporary hack for early exist ...
        ## done = 1

    print " returning map with %d case ids " % len(caseID_map)

    ## TODO: write out this mapping as a two-column output file
    fName = "mapID." + uuid.uuid1().hex + ".tsv"
    fh = file ( fName, 'w' )
    allKeys = caseID_map.keys()
    allKeys.sort()
    for aKey in allKeys:
        fh.write ( '%s\t%s\n' % ( aKey, caseID_map[aKey] ) )
    fh.close()
    sys.exit(-1)

    return ( caseID_map )

## -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

def getCaseAndFileInfo ( cases_endpt, files_endpt, caseID_map ):

    print " "
    print " >>> in getCaseAndFileInfo ... ", cases_endpt, files_endpt, len(caseID_map)
    print " "

    allCases = caseID_map.keys()
    allCases.sort()

    caseID_dict = {}
    fileID_dict = {}

    for case_id in allCases:

        print " "
        print " "
        print " in getCaseAndFileInfo ... looping over allCases ... ", case_id
        caseInfo = get_case_info ( cases_endpt, case_id )

##        try:
##            print " !!! "
##            print caseInfo
##            print caseInfo['sample_ids']
##            print " !!! "
##        except:
##            print " NO sample_ids FOUND in caseInfo "

        if ( case_id not in caseID_dict ):
            print case_id
            print " creating caseID_entry for this case ", case_id
            caseID_dict[case_id] = [ caseInfo ]
        else:
            print " already know about this case ??? !!! "
            print case_id
            print caseID_dict[case_id]
            print caseInfo
            sys.exit(-1)

        filesInfo = get_files_by_case_id ( files_endpt, case_id )

        # parse the files returned above ...
        print " --> got back %d files for this CASE " % len ( filesInfo )
        ## print filesInfo
        for aFile in filesInfo:
            file_id = aFile['file_id']
            if ( file_id not in fileID_dict ):
                print file_id
                print " creating fileID_dict entry for this case ", case_id, file_id
                fileID_dict[file_id] = [ aFile, [ case_id ], [], [] ]
                print fileID_dict[file_id]
            else:
                print " already know about this file ... ", file_id
                curInfo = fileID_dict[file_id][0]
                curCaseList = fileID_dict[file_id][1]
                curSampleList = fileID_dict[file_id][2]
                curSampleList2 = fileID_dict[file_id][3]
                curCaseList += [ case_id ]
                fileID_dict[file_id] = [ curInfo, curCaseList, curSampleList, curSampleList2 ]
                print " AAA " , file_id, len(curCaseList), len(curSampleList)
                print fileID_dict[file_id]

        try:
            print " "
            print " "
            print " SAMPLES for this CASE : "
            print caseInfo['sample_ids']
            print " looping over samples ... "
            numSamples = len ( caseInfo['sample_ids'] )
            for ii in range(numSamples):
                aSample = caseInfo['sample_ids'][ii]
                aSample2 = caseInfo['submitter_sample_ids'][ii]
                print aSample, aSample2
                filesInfoB = get_files_by_sample_id ( files_endpt, aSample )
                print " --> got back %d files for this SAMPLE " % len ( filesInfoB )
                for bFile in filesInfoB:
                    file_id = bFile['file_id']
                    if ( file_id not in fileID_dict ):
                        print file_id
                        print " creating fileID_dict entry for this sample ", aSample, file_id
                        fileID_dict[file_id] = [ aFile, [], [ aSample ], [ aSample2 ] ]
                        print fileID_dict[file_id]
                    else:
                        print " already know about this file ... ", file_id
                        curInfo = fileID_dict[file_id][0]
                        curCaseList = fileID_dict[file_id][1]
                        curSampleList = fileID_dict[file_id][2]
                        curSampleList2 = fileID_dict[file_id][3]
                        curSampleList += [ aSample ]
                        curSampleList2 += [ aSample2 ]
                        fileID_dict[file_id] = [ curInfo, curCaseList, curSampleList, curSampleList2 ]
                        print " BBB ", file_id, len(curCaseList), len(curSampleList)
                        print fileID_dict[file_id]
                    
        except:
            pass

    print " "
    print " returning dicts with %d cases and %d files " % ( len(caseID_dict), len(fileID_dict) )
    print " " 

    return ( caseID_dict, fileID_dict )

## -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

def get_case_info ( cases_endpt, case_id ):

    print " "
    print " >>> in get_case_info ... ", cases_endpt, case_id
    print " "

    global cases_fields

    filt = { 'op': '=',
             'content': {
                 'field': 'case_id',
                 'value': [case_id] } } 

    params = { 'filters': json.dumps(filt) }

    print " get request ", cases_endpt, params
    response = requests.get ( cases_endpt, params=params )
    rj = response.json()
    ## print json.dumps ( rj, indent=4 )

    try:
        if ( len ( rj['data']['hits'] ) != 1 ):
            print " HOW DID THIS HAPPEN ??? more than one case ??? !!! ", len(rj['data']['hits'])
    except:
        pass

    try:
        caseInfo = rj['data']['hits'][0]
        fields = caseInfo.keys()
        fields.sort()

        for aField in fields:
            if ( aField not in cases_fields ): 
                print " adding new field to cases_fields list : ", aField
                cases_fields += [ aField ]

        return ( caseInfo )

    except:
        pass

    return ( {} )

    ## sys.exit(-1)

## -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

def get_files_by_case_id ( files_endpt, case_id ):

    print " "
    print " >>> in get_files_by_case_id ... ", files_endpt, case_id
    print " "

    global files_fields

    filt = { 'op': '=',
             'content': {
                 'field': 'cases.case_id',
                 'value': [case_id] } } 

    params = { 'filters': json.dumps(filt),
               'sort': 'file_id:asc',
               'from': 1,
               'size': 1000 }

    print " get request ", files_endpt, params
    response = requests.get ( files_endpt, params=params )
    rj = response.json()
    ## print json.dumps ( rj, indent=4 )

    try:
        for ii in range(len(rj['data']['hits'])):
            fields = rj['data']['hits'][ii].keys()
            fields.sort()
            for aField in fields:
                if ( aField not in files_fields ): 
                    print " adding new field to files_fields list : ", aField
                    files_fields += [ aField ]
    except:
        pass

    try:
        return ( rj['data']['hits'] )
    except:
        return ( [] )

    ## sys.exit(-1)

## -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

def get_files_by_sample_id ( files_endpt, sample_id ):

    print " "
    print " >>> in get_files_by_sample_id ... ", files_endpt, sample_id
    print " "

    global files_fields

    filt = { 'op': '=',
             'content': {
                 'field': 'cases.samples.sample_id',
                 'value': [sample_id] } } 

    params = { 'filters': json.dumps(filt),
               'sort': 'file_id:asc',
               'from': 1,
               'size': 1000 }

    print " get request ", files_endpt, params
    response = requests.get ( files_endpt, params=params )
    rj = response.json()
    ## print json.dumps ( rj, indent=4 )

    try:
        for ii in range(len(rj['data']['hits'])):
            fields = rj['data']['hits'][ii].keys()
            fields.sort()
            for aField in fields:
                if ( aField not in files_fields ): 
                    print " adding new field to files_fields list : ", aField
                    files_fields += [ aField ]
    except:
        pass

    return ( rj['data']['hits'] )

    ## sys.exit(-1)

## -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

def examineCasesInfo ( caseID_dict ):

    print " "
    print " >>> in examineCasesInfo ... ", len(caseID_dict)
    print " "

    ## let's explore the various properties that have been collected
    ## for each of the CASEs ...

    caseFieldValues = {}
    for aField in cases_fields:
        caseFieldValues[aField] = {}

    for case_id in caseID_dict:
        caseInfo = caseID_dict[case_id]
        for aBlock in caseInfo:
            for aField in cases_fields:
                if ( len(caseFieldValues[aField]) < 50 ):
                    try:
                        aValue = aBlock[aField]
                        if ( aValue not in caseFieldValues[aField] ):
                            caseFieldValues[aField][aValue] = 1
                        else:
                            caseFieldValues[aField][aValue] += 1
                    except:
                        pass

    for aField in cases_fields:
        numV = len ( caseFieldValues[aField] )
        if ( numV > 0 and numV < 50 ):
            print aField, caseFieldValues[aField]
            
    print " "
    print " "

    return

## -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

def examineFilesInfo ( fileID_dict ):

    print " "
    print " >>> in examineFilesInfo ... ", len(fileID_dict)
    print " "

    ## and now let's do the same for each of the FILEs ...

    fileFieldValues = {}
    for aField in files_fields:
        fileFieldValues[aField] = {}

    for file_id in fileID_dict:
        fileInfo = fileID_dict[file_id][0]
        for aField in files_fields:
            if ( len(fileFieldValues[aField]) < 50 ):
                try:
                    aValue = fileInfo[aField]
                    if ( aValue not in fileFieldValues[aField] ):
                        fileFieldValues[aField][aValue] = 1
                    else:
                        fileFieldValues[aField][aValue] += 1
                except:
                    pass

    for aField in files_fields:
        numV = len ( fileFieldValues[aField] )
        if ( numV > 0 and numV < 50 ):
            print aField, fileFieldValues[aField]

    return 

## -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

def writeTable4BigQuery ( caseID_dict, fileID_dict ):

    print " "
    print " >>> in writeTables4BigQuery ... ", len(caseID_dict), len(fileID_dict)
    print " "

    for file_id in fileID_dict:
        fileInfo  = fileID_dict[file_id][0]
        caseList  = fileID_dict[file_id][1]
        sampList  = fileID_dict[file_id][2]
        sampList2 = fileID_dict[file_id][3]

        print " file_id : ", file_id
        print " fileInfo : ", fileInfo
        print " caseList : ", caseList
        print " sampList : ", sampList
        print " sampList2: ", sampList2

        for case_id in caseList:
            print case_id
            print caseID_dict[case_id]

        stopNOW = 0

        ## built up the output line ...
        ## TODO: write this properly to an output file ... also if a value is "None", then do not echo

        outLine = ''
        outLine += '%s' % file_id
        for aField in [ 'submitter_id', 'data_category', 'data_type', 'type', 'file_name', 'experimental_strategy', 'platform', 'access', 'state', 'data_format', 'file_state', 'updated_datetime', 'created_datetime', 'file_size', 'md5sum' ]:
            try:
                outLine += '\t%s' % fileInfo[aField]
            except:
                outLine += '\t'
        outLine += '\t'
        aclInfo = fileInfo['acl']
        for ii in range(len(aclInfo)):
            outLine += '%s' % aclInfo[ii]
            if ( ii < len(aclInfo)-1 ): outLine += ';'
        if ( len(caseList) == 1 ):
            case_id = caseList[0]
            caseInfo = caseID_dict[case_id][0]
            outLine += '\t%s\t%s' % ( case_id, caseInfo['submitter_id'] )
        elif ( len(caseList) == 0 ):
            outLine += '\t\t'
        else:
            outLine += '\tmulti\tmulti'
        if ( len(sampList) == 1 ):
            sample_id = sampList[0]
            sample_id2 = sampList2[0]
            stopNOW = 1
            outLine += '\t%s\t%s' % ( sample_id, sample_id2 )
        elif ( len(sampList) == 0 ):
            outLine += '\t\t'
        else:
            outLine += '\tmulti\tmulti'

        print "OUTLINE:", outLine

        ## if ( stopNOW ): sys.exit(-1)


## -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

def main():

    if ( 0 ):
        cases_endpt = "https://gdc-api.nci.nih.gov/legacy/cases"
        files_endpt = "https://gdc-api.nci.nih.gov/legacy/files"
    else:
        cases_endpt = "https://gdc-api.nci.nih.gov/cases"
        files_endpt = "https://gdc-api.nci.nih.gov/files"

    if ( 1 ):
        caseID_map = get_all_case_ids ( cases_endpt )
        ( caseID_dict, fileID_dict ) = getCaseAndFileInfo ( cases_endpt, files_endpt, caseID_map )

        print " DONE "
        print " "
        cases_fields.sort()
        files_fields.sort()
        print " cases fields : "
        for aField in cases_fields:
            print "     ", aField
        print " "
        print " files fields : "
        for aField in files_fields:
            print "     ", aField
        print " "

    print " "
    print " "

    examineCasesInfo ( caseID_dict )
    examineFilesInfo ( fileID_dict )

    writeTable4BigQuery ( caseID_dict, fileID_dict )

## -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

if __name__ == '__main__':
  main()

## -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
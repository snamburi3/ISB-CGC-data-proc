#!/usr/bin/env python

# Copyright 2015, Institute for Systems Biology.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Script to identify mrna/bcgsc files
"""
from bigquery_etl.utils.gcutils import read_mysql_query
import sys
import json
import re

def identify_data(config):
    """Gets the metadata info from database
    """
    # cloudSql connection params
    host = config['cloudsql']['host']
    database = config['cloudsql']['db']
    user = config['cloudsql']['user']
    passwd = config['cloudsql']['passwd']

    sqlquery = """
        SELECT ParticipantBarcode, SampleBarcode, AliquotBarcode, Pipeline, Platform,
              SampleType, SampleTypeCode, Study, DatafileName, DatafileNameKey, Datatype,
              DatafileUploaded, IncludeForAnalysis, DataCenterName
        FROM metadata_data
        WHERE DataType='Expression-Gene'
        AND DatafileNameKey LIKE '%.gene.quantification.txt'
        AND DatafileUploaded='true'
        AND IncludeForAnalysis='yes'
        """

    # connect to db and get results in a dataframe
    metadata_df = read_mysql_query(host, database, user, passwd, sqlquery)

    # rename platforms in rows
    for i, row in metadata_df.iterrows():
        metadata = row.to_dict()
        if 'IlluminaHiSeq' in metadata['Platform']:
            metadata_df.loc[i, 'Platform'] = 'IlluminaHiSeq'
            platform = 'IlluminaHiSeq'
        elif 'IlluminaGA' in metadata['Platform']:
            metadata_df.loc[i, 'Platform'] = 'IlluminaGA'
            platform = 'IlluminaGA'
        else:
            raise Exception('Did not match any given platform')

        metadata_df.loc[i, 'OutDatafileNameKey'] = config['mrna']['bcgsc']['output_dir']\
                            + platform + '/' + metadata['DatafileName'] + '.json'

    metadata_df.loc[:, 'SampleTypeLetterCode'] = metadata_df['SampleTypeCode']\
                                               .map(lambda code: config['sample_code2letter'][code])

    metadata_df.loc[:, 'DatafileNameKey'] = metadata_df['DatafileNameKey']\
                                               .map(lambda inputfile: re.sub(r"^/", "", inputfile))

    # tag CELLC samples
    metadata_df['is_tumor'] = (metadata_df['SampleTypeLetterCode'] != "CELLC")
    metadata_df['transform_function'] = 'mrna.bcgsc.transform.parse_bcgsc'

    print "Found {0} rows, columns." .format(str(metadata_df.shape))

    # Filter - check all "is_" fields - remember all 'is_' fields must be boolean
    all_flag_columns = [key for key in metadata_df.columns.values if key.startswith("is_")]
    flag_df = metadata_df[all_flag_columns]
    metadata_df = metadata_df[flag_df.all(axis=1)]

    print "After filtering: Found {0} rows, columns." .format(str(metadata_df.shape))

    return metadata_df

if __name__ == '__main__':
    print identify_data(json.load(open(sys.argv[1])))


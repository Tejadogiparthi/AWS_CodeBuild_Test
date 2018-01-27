import boto3
import logging
import sys
from pprint import pprint
import json
from elasticsearch import Elasticsearch, RequestsHttpConnection
# from jose import jws
# import json
# import requests
#
#
# def get_username(authtoken):
#     claims = json.loads(jws.get_unverified_claims(authtoken))
#     return claims['cognito:username']


def setup_logging():
    logger = logging.getLogger()
    for h in logger.handlers:
        logger.removeHandler(h)

    h = logging.StreamHandler(sys.stdout)
    logformat = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    h.setFormatter(logging.Formatter(logformat))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)
    return logger


def connectES(esEndPoint, logger):
    logger.info('Connecting to the ES Endpoint {}'.format(esEndPoint))
    try:
        esClient = Elasticsearch(
            hosts=[{'host': esEndPoint, 'port': 443}],
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection)
        return esClient
    except Exception as E:
        logger.error("Unable to connect to {}".format(esEndPoint))
        logger.error(E)
        exit(3)


def add_user_to_group(requested_db, role_database, userpool_id, username, logger):
    client = boto3.client('cognito-idp')
    # requested_db = tbl_requested.split('.')[0]
    for key in role_database.keys():
        if role_database[key] == requested_db:
            logger.info("The %s database is associated to group %s", requested_db, key)
            client.admin_add_user_to_group(UserPoolId=userpool_id, Username=username, GroupName=key)
            logger.info("Added the user to the group %s", key)


def lambda_handler(event, context):
    pprint(event)
    logger = setup_logging()
    try:

        esclient = connectES("search-adlmanager-elasticsearch-j2fzp2zmuri5t37mqbqq4ukv7u.us-west-2.es.amazonaws.com",
                             logger)
        role_database = {'adlManager_Product1_Group': 'adlmanager_product1_db',
                         'adlManager_Product2_Group': 'adlmanager_product2_db',
                         'adlManager_Product3_Group': 'adlmanager_product3_db'}
        requested_dataset = event['requested_dataset']

        userpool_id = event['UserPoolId']
        user_name = event['User']
        requested_db = requested_dataset.split('.')[0]
        requested_tbl = requested_dataset.split('.')[1]
        add_user_to_group(requested_db, role_database, userpool_id, user_name, logger)
        esdata = {}
        esdata['username'] = user_name
        esdata['dbname'] = requested_db
        esdata['tablename'] = requested_tbl
        json_data = json.dumps(esdata)
        pprint(json_data)
        unique_id = user_name + "_" + requested_db + "_" + requested_tbl
        esclient.index(index="adlmanager_user_favorites", doc_type="favorites", body=json_data, id=unique_id)
        return "Successfully granted the access to the user."
    except Exception as E:
        logger.error(E)
        exit(3)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# Import Modules
import requests
import pandas as pd
import re
import os
from io import StringIO


###--------------------------------Classes--------------------------------###

# Login Session
class Session:
    
    # Constructor
    def __init__(self, server: str, session_id: str):
        self.server = server
        self.id = session_id
        try:
            self.instance = re.search("http[s]*://(.+)\.salesforce", server).group(1)
        except Exception:
            self.instance = None
    
    # String Representation
    def __repr__(self):
        return "ID: {}\nServer:{}".format(self.id, self.server)

# Bulk Job
class Job:
    
    # Constructor
    def __init__(self, job_id: str, operation: str, sfobject: str, session: Session):
        self.job_id = job_id
        self.operation = operation.lower()
        self.sfobject = sfobject
        self.session = session
        
        
    # String Representation
    def __repr__(self):
        return "ID: {}\nOperation: {}\nObject: {}".format(self.job_id, self.operation, self.sfobject)


    # Close Job
    def close(self, session = None):
        
        if session is None:
            session = self.session
        
        # Define POST Request URL
        post_url = r"https://{}.salesforce.com/services/async/47.0/job/{}".format(session.instance, self.job_id)

        # Define Header
        header = {"X-SFDC-Session": session.id,
                  "Content-Type": "application/xml; charset=UTF-8"}
        
        # Create Configuration XML
        close_config = """<?xml version="1.0" encoding="UTF-8"?>
        <jobInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">
            <state>Closed</state>
        </jobInfo>"""
        
        # Make POST Request
        response = requests.post(post_url, headers = header, data = close_config)
        
        try:
            exception_msg = re.search("<exceptionMessage>(.+)<exceptionMessage>", response.text).group(1)
        except Exception:
            exception_msg = None
            
        if exception_msg is not None:
            raise RuntimeError(exception_msg)
        else:
            print("Job {} closed".format(self.job_id))
          
            
    # Add Batch to Job
    def add_batch(self, batch, session = None):
        
        # Parse Input
        if session is None:
            session = self.session
            
        # Parse Batch Data
        if type(batch) is pd.DataFrame:
            batch_size = batch.shape[0]
            if batch_size > 10000:
                raise RuntimeError("The size of your batch should be less than 10000."+
                                   "Consider splitting your data in multiple batches.")
            batch = batch.to_csv(index = False, encoding = "utf-8")
        elif os.path.isfile(batch) and batch.endswith(".csv"):
            with open(batch, mode = "rt", encoding = "utf-8") as f:
                batch = f.read()
                batch_size = len(batch.split("\n")) - 1
                if batch_size  > 10000:
                    raise RuntimeError("The size of your batch should be less than 10000."+
                                       "Consider splitting your data in multiple batches.")
        elif type(batch) is str and self.operation == "query":
            batch = batch
        else:
            raise ValueError("Please provide either a Pandas DataFrame, the path to a csv file, "+
                             "or a SOQL command if you query.")
        
        # Define URL for POST Request
        post_url = "https://{}.salesforce.com/services/async/47.0/job/{}/batch".format(session.instance, self.job_id)
        
        # Define Header
        header = {"X-SFDC-Session": session.id,
                  "Content-Type": "text/csv; charset=UTF-8"}
        
        # Make POST Call
        response = requests.post(post_url, headers = header, data = batch)
        
        try:
            exception_msg = re.search("<exceptionMessage>(.+)<exceptionMessage>", response.text).group(1)
        except Exception:
            exception_msg = None
            
        if exception_msg is not None:
            raise RuntimeError(exception_msg)
            
            
    # Update Status
    def get_status(self, session = None):
        
        # Parse Input
        if session is None:
            session = self.session
        
        # Define Header
        header = {"X-SFDC-Session": session.id}
        
        # Create URL for GET Request
        get_url = "https://{}.salesforce.com/services/async/47.0/job/{}/batch".format(session.instance, self.job_id)
        
        # Make GET Request
        response = requests.get(get_url, headers = header)
        
        # Parse Response
        response_clean = re.sub("\n", "", response.text)
        batches = re.findall("<batchInfo>(.+?)</batchInfo>", response_clean)
        
        batch_status = []
        for b in batches:
            batch_id = re.search("<id>(.+)</id>", b).group(1)
            status = re.search("<state>(.+)</state>", b).group(1)
            message = re.search("<stateMessage>(.+)</stateMessage>", b)
            if message is None:
                message = ""
            else:
                message = message.group(1)
            processed = re.search("<numberRecordsProcessed>(.+)</numberRecordsProcessed>", b).group(1)
            status_dict = {"id": batch_id, "status": status, 
                           "message": message, "processed": int(processed)}
            batch_status.append(status_dict)
        
        # Return Status as List of Dict
        return batch_status
    
    
    # Fetch Results
    def get_results(self, session = None):
        
        # Parse Input
        if session is None:
            session = self.session
        
        # Check that all Batches are processed
        current_status = self.get_status(session)
        if self.operation == "query":
            current_status = current_status[1:]
        status_list = [x["status"] for x in current_status]
        
        if not all([x in ["Completed", "Failed"] for x in status_list]):
            print("Not all Batches are done yet")
            return None
        else:
            batches = [x["id"] for x in current_status]
            
        results = []
        for b in batches:
            
            # Define URL for GET request
            get_url = "https://{}.salesforce.com/services/async/47.0/job/{}/batch/{}/result".format(session.instance, self.job_id, b)
            
            # Define Header
            header = {"X-SFDC-Session": session.id}
            
            # Make GET Request
            response = requests.get(get_url, headers = header)
            if self.operation == "query":
                result_id = re.search("<result>(.+)</result>", response.text).group(1)
                get_url = "https://{}.salesforce.com/services/async/47.0/job/{}/batch/{}/result/{}".format(session.instance, self.job_id, b, result_id)
                response = requests.get(get_url, headers = header)
            response_io = StringIO(response.text)
            response_pd = pd.read_csv(response_io, encoding = "utf-8")
            results.append(response_pd)
  
        # Return Result as Pandas DataFrame
        result_pd = pd.concat(results)
        return result_pd

###--------------------------------Functions--------------------------------###

# Login
def login(username: str, password: str, token: str):
    
    # Create Login XML
    login_xml = r"""<?xml version="1.0" encoding="utf-8" ?>
    <env:Envelope xmlns:xsd="http://www.w3.org/2001/XMLSchema"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:env="http://schemas.xmlsoap.org/soap/envelope/">
        <env:Body>
            <n1:login xmlns:n1="urn:partner.soap.sforce.com">
                <n1:username>{}</n1:username>
                <n1:password>{}</n1:password>
            </n1:login>
        </env:Body>
    </env:Envelope>""".format(username, password+token)
    
    # Define Header
    header = {"Content-Type": "text/xml;charset=UTF-8",
              "SOAPAction": "login"}

    # Make Post Request
    response = requests.post("https://login.salesforce.com/services/Soap/u/47.0",
                             headers = header, data = login_xml)
    
    # Parse Login Result
    try:
        server_url = re.search("<serverUrl>(.+)</serverUrl>", response.text).group(1)
    except Exception:
        server_url = None
    
    try:
        session_id = re.search("<sessionId>(.+)</sessionId>", response.text).group(1)
    except Exception:
        session_id = None
    
    # Return Login Result as Dict
    return (Session(server = server_url, session_id = session_id))


# Creating a Job
def create_job(operation: str, sfobject: str, session: Session, chunk_size: int = 1000):
    
    # Check if opeation in allowed
    operation = operation.lower()
    operations_allowed = ["insert", "update", "delete", "query"]
    if operation not in operations_allowed:
        raise ValueError("Operation {} not supported. Please choose either: "+
                         "'insert', 'update', 'delete', or 'query'")
    
    
    # Creation XML
    if operation != "query":
        creation_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <jobInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">
            <operation>{}</operation>
            <object>{}</object>
            <contentType>CSV</contentType>
        </jobInfo>""".format(operation, sfobject)
    else:
        creation_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <jobInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">
            <operation>{}</operation>
            <object>{}</object>
            <concurrencyMode>Parallel</concurrencyMode>
            <contentType>CSV</contentType>
        </jobInfo>""".format(operation, sfobject)
    
    # Create Header for Post Request
    header = {"X-SFDC-Session": session.id, 
              "Content-Type": "application/xml; charset=UTF-8"}
        
    if (operation == "query"):
        header["Sforce-Enable-PKChunking"]  = "chunkSize={}".format(str(chunk_size))

    # Define POST Request URL
    post_url = r"https://{}.salesforce.com/services/async/47.0/job".format(session.instance)

    # Make POST Request
    response = requests.post(post_url, headers = header, data = creation_xml)
    
    # Parse Response
    try:
        job_id = re.search("<id>(.+)</id>", response.text).group(1)
    except Exception:
        job_id = None
    
    try:
        exception_msg = re.search("<exceptionMessage>(.+)</exceptionMessage>", response.text).group(1)
    except Exception:
        exception_msg = None
        
    if job_id is not None:
        return Job(job_id, operation, sfobject, session)
    else:
        raise RuntimeError(exception_msg)
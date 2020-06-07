#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# Import Modules
import requests
import pandas as pd
import re
import os
import time
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
    def close(self, session = None, verbose = True):
        
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
            if verbose:
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
    def get_results(self, session = None, batches_ignore = []):
        
        # Parse Input
        if session is None:
            session = self.session
        
        # Check that all Batches are processed
        status = self.get_status(session)
        batches = [x["id"] for x in status if x["id"] not in batches_ignore and x["processed"] > 0]
        results = []
        
        # Fetch Results
        for b in batches:
            
            # Define URL for GET request
            get_url = "https://{}.salesforce.com/services/async/47.0/job/{}/batch/{}/result".format(session.instance, self.job_id, b)
            
            # Define Header
            header = {"X-SFDC-Session": session.id}
            
            # Make GET Request
            response = requests.get(get_url, headers = header)
            if self.operation == "query":
                result = re.search("<result>(.+)</result>", response.text)
                if result is not None:
                    result_id = result.group(1)
                    get_url = "https://{}.salesforce.com/services/async/47.0/job/{}/batch/{}/result/{}".format(session.instance, self.job_id, b, result_id)
                    response = requests.get(get_url, headers = header)
            
            # Parse Response
            if "exceptionMessage" in response.text:
                exception = re.search("<exceptionMessage>(.+)</exceptionMessage>", response.text).group(1)
                raise ValueError(exception)
            else:
                response_io = StringIO(response.text)
                response_pd = pd.read_csv(response_io, encoding = "utf-8")
                results.append(response_pd)
  
        # Return Result as Pandas DataFrame
        result_pd = pd.concat(results)
        return result_pd

###--------------------------------Functions--------------------------------###

# Login
def login(username: str, password: str, token: str):
    """ Used to log into SalesForce. Will return an instance
    of the Session object. Must be used for every interaction
    with SalesForce.
    
    Parameters
    ----------
    username: str
        You username that you use to log into SalesForce.
    
    password: str
        The password you use to log into SalesFroce with the 
        specified username.
        
    token: str
        The security token you have received for your SalesForce
        account. Normally, this is sent via email after every
        password change. Check that your org has security tokens
        activated.
        
    Returns
    ----------
    session: Session
        An instance of the Session class. This instance must be
        passed into every push or pull operation that you use.
    """
    
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
    """Creates a job on the SalesForce Data Cloud. This is a
    prerequesit for every operation.
    
    Parameters
    ----------
    operation: str
        One of either 'insert', 'update', 'delete', or 'query'.
        
    sfobject: str
        The name of the SalesForce object you want to operate on.
        
    session: Session
        An active instance of the Session class. Use the login()
        function to create one. This object holds your credentials.
        
    chunk_size: int
        If your operation is 'query', the results will be split
        into multiple batches of size equal to 'chunk_size'.
        This will increase performance for large chunks of data
        since it will be downloaded in separate chunks. Will be
        ignored, if operation is not 'query'.
        
    Returns
    ----------
    job: Job
        An instance of the Job class. All further interaction
        with SalesForce will happen via the interface of this instance.
    """
    
    # Check if opeation in allowed
    operation = operation.lower()
    operations_allowed = ["insert", "update", "delete", "query"]
    if operation not in operations_allowed:
        raise ValueError("Operation {} not supported. Please choose either: ".format(operation) +
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
        

# Turn Data into Batches
def _batchify(data, batch_size: int, sep = ",", encoding = "utf-8"):
    
    # Read in CSV file
    if type(data) is str and os.path.isfile(data) and data.endswith(".csv"):
        data = pd.read_csv(data, sep = sep, encoding = encoding)
        
    # Chunk Data into Batches
    pos = 0
    batches = []
    size = data.shape[0]
    while pos < size:
        batches.append(data.iloc[pos:pos+batch_size])
        pos += batch_size
        
    return batches


# API for getting Data into SalesForce
def push(operation: str, sfobject: str, data, session: Session, 
         batch_size = 1000, sep = ",", encoding = "utf-8", verbose = False):
    """Used to push data into SalesForce and trigger changes
    inside the SalesForce Data Cloud.
    
    Parameters
    ----------
    operation: str
        Either one of 'insert', 'update', or 'delete'.
        
    sfobject: str
        The name of the SalesForce object you want to operate on.
        
    data: pandas.DataFrame or FilePath
        The data you want to push into SalsForce. This can either
        be a Pandas DataFrame or the path to a csv file. Note
        that if you give a csv file path, the data will be
        loaded into a Pandas DataFrame for you.
        
    session: Session
        An active instance of the Session class. Use the login()
        function to create one. This object holds your credentials.
        
    batch_size: int
        Your input will be split into batches of this size. This
        is done to speed up upload time.
        
    sep: str
        If you give a csv file path for the data argument, this
        is the field separator used in your csv file.
        
    encoding: str
        If you give a csv file path for the data argument, this
        is the file's encoding.
        
    verbose: Boolean
        If set to True, you will receive further information
        about your workload. Very useful for debugging.
        
    Returns
    ----------
    result: pandas.DataFrame
        A Pandas DataFrame holding the results and IDs of the
        data that you have pushed into SalesForce.
    """
    
    # Create Job
    job = create_job(operation, sfobject, session)
    
    # Split Data into Batches
    batches = _batchify(data, batch_size, sep = sep, encoding = encoding)
            
    # Add Single Batches to Job
    for batch in batches:
        job.add_batch(batch)
        
    # Close Job
    job.close(verbose = verbose)
    
    # Get Status
    complete = False
    while not complete:
        status_messages = job.get_status()
        processed = sum([x["processed"] for x in status_messages ])
        print("\rProcessed {} entries".format(processed), end = "")
        completed = len([x for x in status_messages if x["status"] in ["Completed", "Failed"]])
        complete = int(len(status_messages)) == int(completed)
    
    # Print Final Status Report
    if verbose:
        print("Final Status Report:")
        for i in status_messages:
            print(i)
    
    # Return Result
    return job.get_results()


# API for getting Data from SalesForce
def pull(query: str, sfobject: str, session: Session, chunk_size = 1000, verbose = False):
    """Used to pull data from SalesForce into a Pandas DataFrame.
    
    Parameters
    ----------
    query: str
        An SOQL query you would like to run on the SalesForce
        DataCloud.
        
    sfobject: str
        The name of the SalesForce object you want to query.
        
    session: Session
        An active instance of the Session class. Use the login()
        function to create one. This object holds your credentials.
        
    chunk_size: int
        Your output will be split into batches of this size. This
        is done to speed up download time. The final result will
        be a single Pandas DataFrame holding the data from all
        chunks.
        
    verbose: Boolean
        If set to True, you will receive further information
        about your workload. Very useful for debugging. Note that
        you will receive a final status report. If everything worked,
        all batches will be 'Finished' but one. One batch will show
        the status 'Not Processed'. This is your query trigger and 
        it is completely expected.
        
    Returns
    ----------
    result: pandas.DataFrame
        A Pandas DataFrame holding the results of your query.
    """
    
    # Sanity Check for Query
    if not "select" in query.lower() or "from" not in query.lower():
        raise ValueError("Something seems wrong with your query")
    
    # Create Job
    job = create_job("query", sfobject, session, chunk_size)
    
    # Add Query as a Batch
    job.add_batch(query)

    # Sleep so Server can Catch Up
    time.sleep(1)

    # Get Status
    complete = False
    while not complete:
        status_messages = job.get_status()
        init_batch, init_status, init_message = [(x["id"], x["status"], x["message"]) for x in status_messages if x["status"] == "NotProcessed" and x["processed"] == 0][0]
        if init_status == "Failed":
            raise RuntimeError(init_message)
        processed = sum([x["processed"] for x in status_messages ])
        print("\rProcessed {} entries".format(processed), end = "")
        completed = len([x for x in status_messages if x["status"] in ["Completed", "Failed"]]) + 1
        if completed > 1:
            complete = int(len(status_messages)) == int(completed)
    print("")
            
    # Close Job
    job.close(verbose = verbose)
        
    # Print Final Status Report
    if verbose:
        print("Final Status Report:")
        for i in status_messages:
            print(i)
    
    # Return Result
    return job.get_results(batches_ignore = [init_batch])
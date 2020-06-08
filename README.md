# PandasForce
This is an integration of SalesForce and Pandas for Python. It is using SalesForce's Bulk API for loading data from Pandas DataFrames into SalesForce and loading data from SalesForce into Pandas dataframes. There is a high level API consisting of the push() and pull() functions as well as a more low level implementation.

Using the Bulk API is encouraged if you want to work with multiple rows of data. The Bulk API was optimized to handle even large amounts of data. If you are currently using SalesForce's REST API for transferring large amounts of data, you should see significant increases in performance.

## Installation
You can install PandasForce by using pip
```pip install pandasforce```

However, if you decide to import the source code, make sure that the following dependencies are installed:
* requests
* pandas

## Usage

The following imports are taken as given:
```import pandas as pd
import pandasforce as pf```

#### High Level API
In order to interact with your orgs data cloud, you need to create an active session by logging in. Assume that your user account is "john.doe@test.com" and your password is "Test12345" and that your security token is equal to "Hello123". Use the login(username, password, token) function to create an active session:
```session = pf.login(username = "john.doe@test.com", password = "Test12345", token = "Hello123")```

Now you can either use the push() function to change data inside SalesForce or pull() to get data from SalesForce. Let's assume that you create a pandas DataFrame holding information on leads and you want to insert those leads into SalesForce:

```
companies = ["Test Inc", "Doe AG", "Mustermann KG"]
lnames = ["Musterfrau", "Doe","Mustermann"]
fnames = ["Eva", "John", "Max"]
leads = pd.DataFrame({"Company": companies,
		      "LastName": lnames,
		      "FirstName": fnames})
leads_insert = pf.push(operation = "insert", sfobject = "lead", data = leads,
		       session = session)
```

This will insert the data into SalesForce. The push() function takes the following parameters:
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

The result will be a Pandas DataFrame holding the results and IDs of the data that you have pushed into SalesForce.

If you decide to query data residing in your SalesForce data cloud, you can use the pull() function. These are the parameters of the function:

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

The result will be a Pandas DataFrame holding the results of your SOQL query. Note that your query must be valid SOQL. SOQL only supports a subset of normal SQL commands. Assume that we want to extract the company name, the first name, and the last name of all our leads. Also, we are going to use the session previously defined:
```leads = pf.pull(query = "SELECT Company,FirstName,LastName FROM Lead", sfobject = "lead", session = session)```
leads will be a regular Pandas DataFrame holding all of our leads.

#### Low Level API
If you wish to have more control over your operations, you can opt to use a more low-level API. Note that the push() and pull() functions are simple wrappers.

Creating a session is the same as for the high level api. Create a session by logging in:
```session = pf.login(username = "john.doe@test.com", password = "Test12345", token = "Hello123")```

The next step will be to create a job. This job will be our point of interaction with SalesForce's Bulk API. The create_job() functions takes the following parameters:

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

Let's say you would like to insert some leads into SalesForce. First, we need to create a job after logging in:

```job = pf.create_job(operation = "insert", sfobject = "lead", session = session)```

Next, we need to insert some data as batches to our job. This can be done by using the add_batch() method which takes either a Pandas DataFrame or the path to a csv file.

```df = pd.DataFrame({"Company": ["A", "B", "C"],
		      "FirstName": ["John", "Jack", "Sarah"],
		      "LastName": ["Doe", "Smith", "Miller"]}) 
job.add_batch(df)```

Note that it is encouraged to split your data into multiple batches. This will speed up processing. Also, your batch must not be larger than 10000 observations.

When all batches are added to your job, you must close the job by using the close() method.
```job.close()```

You can look up the progress of your job by running the get_status() method. This will return a list of dictionaries. Every dictionary represents a single batch and contains information on the current status as well as how many items have been processed yet. If you are quering data, note that there will always be one batch with status "Not Processed" and 0 processed items. This is the initial batch that creates all other batches.
```job.get_status()```

When all batches are processed sucessfully, you can obtain the results by calling the get_results() method. The result will be a Pandas DataFrame holding the IDs for insert, update, and delete operations. If your job is a query, it will hold the result of your SOQL query.
```job.get_results()```

## References
This modules was built by using SalesForce's official [Bulk API Documentation](https://developer.salesforce.com/docs/atlas.en-us.api_asynch.meta/api_asynch/).

# PandasForce
This is an integration of SalesForce and Pandas for Python. It is using SalesForce's Bulk API for loading data from Pandas DataFrames into SalesForce and loading data from SalesForce into Pandas dataframes. There is a high level API consisting of the push() and pull() functions as well as a more low level implementation.

Using the Bulk API is encouraged if you want to work with multiple rows of data. The Bulk API was optimized to handle even large amounts of data. If you are currently using SalesForce's REST API for transfering large amounts of data, you should see significatn increases in performance.

## Installation
You can install PandasForce by using pip
``` pip install pandasforce ```

However, if you decide to import the source code, make sure that the following dependencies are installed:
* requests
* pandas

## Usage

#### High Level API
In order to interact with your orgs Data Cloud, you need to create an active session by logging-in. Assume that your user account is john.doe@test.com and your password is Test12345 and that your security token is equal to Hello123. Use the login(username, password, token) function to create an active session:
``` session = login(username = "john.doe@test.com", "Test12345", "Hello123") ```

Now you can either use the push() function to change data inside SalesForce or pull() to get data from SalesForce. Let's assume that you create a pandas DataFrame holding information on leads and you want to insert those leads into SalesForce:

```
companies = ["Test Inc", "Doe AG", "Mustermann KG"]
lnames = ["Musterfrau", "Doe","Mustermann"]
fnames = ["Eva", "John", "Max"]
leads = pd.DataFrame({"Company": companies,
		      "LastName": lnames,
		      "FirstName": fnames})
leads_insert = push(operation = "insert", sfobject = "lead", data = leads,
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
```leads = pull(query = "SELECT Company,FirstName,LastName FROM Lead", sfobject = "lead", session = session)```
leads will be a normal Pandas DataFrame holding all of our leads.

We need to to take into account when we run unit test, chroma does not allow you to have a running instance of chromadb, you need to make a new one each timeyou run a test, and make it temporary. 

We can use a temporary directory for the chromadb instance, and make sure to clean it up after the test. 
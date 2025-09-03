README

**IMPORTANT**
Please note that the API key I received from ACRCloud for song identification will expire on **3/24**, so the app may not work properly after this time. If grading is occurring after this time, I hope the demo I have provided is sufficient to understand the client-side functionalities.

To run the app's client, run the python file, which will be able to connect to the server and work properly.
To setup the app's server - 
You will need to configure the following AWS resources:

1. **S3 Bucket**
   - Name: `photoapp-max-nu-cs310`
   - Used for storing uploaded audio files.
   - Files go into the `uploads/` folder.

2. **RDS (MySQL) Database**
   - Use the provided `tunefinder sql.sql` to create:
     - `jobs` table (stores uploaded file metadata)
     - `songs` table (stores song results)
     - Create users `tunefinder-read-only` and `tunefinder-read-write`

3. **Lambda Functions**
   - Set up the three lambda functions - tunefinder_upload, tunefinder_songs, and tunefinder_identify, with the included files and config
   - Add environment variables to tunefinder_identify function:
     - `API_HOST`, `API_ACCESS_KEY`, `API_SECRET_KEY` (for ACRCloud)

4. **Layers**
   - Add a layer for FFmpeg binaries, MySQL, as well as requests and cryptography for RDS access

5. **API Gateway**
   - Create REST API with routes:
     - `POST /upload` - triggers `tunefinder_upload`
     - `POST /identify` - triggers `tunefinder_identify`
     - `GET /songs` - triggers `tunefinder_songs`
   - Enable Lambda proxy integration
   - Make sure IAM permissions allow `apigateway.amazonaws.com` to invoke functions, I created policies for each of the functions

Run the client:
   python3 main.py

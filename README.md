# CDN Optimization

Experiments with Media over QUIC relay topology optimization.

## Run

Note that the [requirements.txt](requirements.txt) and this [section](#run) only considers the running of the API and its testbed.
Other utilities such as the plotter may require additional dependencies.

### Docker (preferred)
 * Build the image: `docker build -t cdn-optimization .`
 * Run a container: `docker run --name cdn-api --rm -p 80:80 cdn-optimization`

### Locally
 * Create a virtual environment: `python -m venv venv`
 * Activate the virtual environment: `venv...`
   * Depending on the platform you're using, you might want to run: `/bin/activate`/`\Scripts\activate.bat`/`\Scripts\Activate.ps1`
   * You can deactivate it later by running the command: `deactivate`
 * Install dependencies: `pip install -r requirements.txt`
 * Run the script: `python -m fastapi dev app/api.py`

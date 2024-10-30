# CDN Optimization

Experiments with Media over QUIC relay topology optimization.
This project is strongly related to [1majom's moq-rs fork](https://github.com/1majom/moq-rs).

## Development 

When using Docker Compose for development, it's useful to just simply link the required .env to the sample environment file provided: `ln -s example.env .env`

## Run

Note that the [requirements.txt](requirements.txt) and this [section](#run) only considers the running of the API and its testbed.

### Docker (preferred)

Either build the container for yourself...
 * Build the image: `docker build -t cdn-optimization .`
Or run the latest published version from [Docker Hub](https://hub.docker.com/r/zoltan120/cdn-optimization)...
 * Pull the image: `docker pull zoltan120/cdn-optimization`

After acquiring an image, run a container instance of it:
 * Run a container: `docker run --rm -p 80:80 -e TOPOFILE=small_topo.yaml -v ./datasource:/code/datasource --name cdn-api cdn-optimization`

| Parameter | Function |
| :----: | --- |
| `-p 80` | API server |
| `-e TOPOFILE=small_topo.yaml` | for changing the network topology used by the API |
| `-v /code/datasource` | Location of graph and topology descriptions on disk. |

### Locally
 * Create a virtual environment: `python -m venv venv`
 * Activate the virtual environment: `venv...`
   * Depending on the platform you're using, you might want to run: `/bin/activate`/`\Scripts\activate.bat`/`\Scripts\Activate.ps1`
   * You can deactivate it later by running the command: `deactivate`
 * Install dependencies: `pip install -r requirements.txt`
 * Run the script: `python -m fastapi run app/api.py --port 80`

import os
from dotenv import load_dotenv
from mem0 import Memory
import requests
from requests.exceptions import RequestException
import logging

load_dotenv()

#Set up logging
# logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)



def verify_qdrant_connection(url: str, api_key: str) -> bool:
    try:
        headers = {"api-key": api_key}
        response = requests.get(f"{url}/healthz", headers=headers, timeout=5)
        logger.debug(f"Qdrant health check response: {response.status_code}")
        return response.status_code == 200
    except RequestException as e:
        logger.error(f"Qdrant connection error: {str(e)}")
        return False

config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "host": "qdrant.gabrielmalek.com",
            "port": 443,
            "api_key": os.getenv("QDRANT_API_KEY")
        }
    },
    "llm": {
        "provider": "litellm",
        "config": {
            "api_key": os.getenv("GEMINI_API_KEY"),
            "model": "gemini/gemini-2.0-flash-lite"
        }
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "model": "text-embedding-3-small"
        }
    },
    "graph_store": {
        "provider": "neo4j",
        "config": {
            "url": os.getenv("NEO4J_URL"),
            "username": os.getenv("NEO4J_USERNAME"),
            "password": os.getenv("NEO4J_PASSWORD")
        }
    },
    "history_db_path": "db/history.db",
    "version": "v1.1",
}
# m = Memory.from_config(config)


try:
    qdrant_url = f"https://{config['vector_store']['config']['host']}"
    qdrant_api_key = config["vector_store"]["config"]["api_key"]
    
    logger.debug(f"Attempting to connect to Qdrant at {qdrant_url}")
    if not verify_qdrant_connection(qdrant_url, qdrant_api_key):
        raise ConnectionError("Could not connect to Qdrant server")
    
    logger.debug("Initializing Memory client...")
    m = Memory.from_config(config)
    logger.debug("Memory client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Memory: {str(e)}", exc_info=True)
    m = None



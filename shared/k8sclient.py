from kubernetes import client, config
import logging
logger = logging.getLogger(__name__)

class Client:
    k8s: client.CoreV1Api
    crd: client.CustomObjectsApi

    def __initialize_config(self):
        try:
            config.load_incluster_config()
            logger.debug("Loaded incluster config")
        except Exception:
            ...
        try:
            config.load_kube_config()
        except Exception:
            logger.error("Failed to load kube config")
            raise

    def __init__(self):
        self.__initialize_config()
        self.k8s = client.CoreV1Api()
        self.crd = client.CustomObjectsApi()

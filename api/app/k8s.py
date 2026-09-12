from kubernetes import client, config


def load_k8s_config() -> None:
    try:
        config.load_kube_config()
    except config.ConfigException:
        config.load_incluster_config()


def custom_objects_api() -> client.CustomObjectsApi:
    return client.CustomObjectsApi()


def core_v1_api() -> client.CoreV1Api:
    return client.CoreV1Api()

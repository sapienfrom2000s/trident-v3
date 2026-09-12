from unittest.mock import patch

from kubernetes import config

from app.k8s import load_k8s_config


def test_load_k8s_config_prefers_kubeconfig() -> None:
    with (
        patch.object(config, "load_kube_config") as load_kube_config,
        patch.object(config, "load_incluster_config") as load_incluster_config,
    ):
        load_k8s_config()

    load_kube_config.assert_called_once()
    load_incluster_config.assert_not_called()


def test_load_k8s_config_falls_back_to_incluster_config() -> None:
    with (
        patch.object(config, "load_kube_config", side_effect=config.ConfigException),
        patch.object(config, "load_incluster_config") as load_incluster_config,
    ):
        load_k8s_config()

    load_incluster_config.assert_called_once()

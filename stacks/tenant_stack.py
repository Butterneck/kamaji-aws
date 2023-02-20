from aws_cdk import (
    Stack,
    aws_eks as eks,
    aws_ssm as ssm,
)
from constructs import Construct
from utils.utils import TenantConfig


class TenantStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, tenant_config: TenantConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        admin_cluster_name = ssm.StringParameter.value_for_string_parameter(
            self, "/eks/admin-cluster/name")
        admin_cluster_kubectl_role_arn = ssm.StringParameter.value_for_string_parameter(
            self, "/eks/admin-cluster/kubectl/role/arn",
        )

        admin_cluster = eks.Cluster.from_cluster_attributes(
            self, "admin-cluster",
            cluster_name=admin_cluster_name,
            kubectl_role_arn=admin_cluster_kubectl_role_arn,
        )

        eks.KubernetesManifest(
            self,
            f"{tenant_config.namespace}-{tenant_config.name}-tcp",
            cluster=admin_cluster,
            manifest=[
                {
                    "apiVersion": "kamaji.clastix.io/v1alpha1",
                    "kind": "TenantControlPlane",
                    "metadata": {
                        "name": tenant_config.name,
                        "namespace": tenant_config.namespace
                    },
                    "spec": {
                        "dataStore": "default",
                        "controlPlane": {
                            "deployment": {
                                "replicas": 3,
                                "additionalMetadata": {
                                    "labels": {
                                        "tenant.clastix.io": tenant_config.name
                                    }
                                },
                                "extraArgs": {
                                    "apiServer": [],
                                    "controllerManager": [],
                                    "scheduler": []
                                },
                                "resources": {
                                    "apiServer": {
                                        "requests": {
                                            "cpu": "250m",
                                            "memory": "512Mi"
                                        },
                                        "limits": {}
                                    },
                                    "controllerManager": {
                                        "requests": {
                                            "cpu": "125m",
                                            "memory": "256Mi"
                                        },
                                        "limits": {}
                                    },
                                    "scheduler": {
                                        "requests": {
                                            "cpu": "125m",
                                            "memory": "256Mi"
                                        },
                                        "limits": {}
                                    }
                                }
                            },
                            "service": {
                                "additionalMetadata": {
                                    "labels": {
                                        "tenant.clastix.io": tenant_config.name
                                    }
                                },
                                "serviceType": "LoadBalancer"
                            }
                        },
                        "kubernetes": {
                            "version": tenant_config.version,
                            "kubelet": {
                                "cgroupfs": "systemd"
                            },
                            "admissionControllers": [
                                "ResourceQuota",
                                "LimitRanger"
                            ]
                        },
                        "networkProfile": {
                            "port": tenant_config.port,
                            "certSANs": [
                                f"{tenant_config.name}.{tenant_config.domain}",
                            ],
                            "serviceCidr": tenant_config.svc_cidr,
                            "podCidr": tenant_config.pod_cidr,
                            "dnsServiceIPs": [
                                tenant_config.dns_service
                            ]
                        },
                        "addons": {
                            "coreDNS": {},
                            "kubeProxy": {},
                            "konnectivity": {
                                "server": {
                                    "port": tenant_config.proxy_port,
                                    "resources": {
                                        "requests": {
                                            "cpu": "100m",
                                            "memory": "128Mi"
                                        },
                                        "limits": {}
                                    }
                                }
                            }
                        }
                    }
                }
            ]
        )

        # Add nodegroup that connects to this tcp

        # Query object to get kubeconfig and token https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_eks-readme.html#querying-kubernetes-resources

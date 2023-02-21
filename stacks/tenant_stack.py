from aws_cdk import (
    Stack,
    aws_eks as eks,
    aws_ssm as ssm,
    aws_autoscaling as autoscaling,
    aws_ec2 as ec2,
    aws_s3_assets as assets,
    Fn,
    CfnOutput,
)
from constructs import Construct
from utils.utils import TenantConfig

class TenantStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, tenant_config: TenantConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get admin cluster informations
        admin_cluster_name = ssm.StringParameter.value_for_string_parameter(
            self, "/eks/admin-cluster/name")
        admin_cluster_kubectl_role_arn = ssm.StringParameter.value_for_string_parameter(
            self, "/eks/admin-cluster/kubectl/role/arn",
        )
        # admin_cluster_vpc_id = ssm.StringParameter.value_from_lookup(
        #     self, "/eks/admin-cluster/vpc/id",
        # )
        admin_cluster = eks.Cluster.from_cluster_attributes(
            self, "admin-cluster",
            cluster_name=admin_cluster_name,
            kubectl_role_arn=admin_cluster_kubectl_role_arn,
            # vpc=ec2.Vpc.from_lookup(self, 'admin-cluster-vpc', vpc_id=admin_cluster_vpc_id)
        )

        # Create namespace for the tenant
        namespace = eks.KubernetesManifest(
            self,
            f"{tenant_config.name}-namespace",
            cluster=admin_cluster,
            manifest=[
                {
                    "apiVersion": "v1",
                    "kind": "Namespace",
                    "metadata": {
                        "name": tenant_config.namespace,
                    },
                },
            ],
        )

        # Actually create the tenant
        tenant_control_plane = eks.KubernetesManifest(
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
                                "serviceType": "ClusterIP"
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

        tenant_control_plane.node.add_dependency(namespace)


        # Worker nodes join

        # Bootstrap nodes in the tenant's autoscaling group
        # user_data = ec2.UserData.for_linux()
        # host_bootstrap_script = assets.Asset(self, "host-bootstrap-script", path="stacks/bootstrap_tenant_host.sh")
        # user_data.add_s3_download_command(bucket=host_bootstrap_script.bucket, bucket_key=host_bootstrap_script.s3_object_key)
        # user_data.add_commands("set -o xtrace", f"/tmp/{host_bootstrap_script.s3_object_key} {tenant_config.version}")

        # Get kubeconfig for the tcp and write it on the nodes
        # tcp_kubeconfig = eks.KubernetesObjectValue(self, "join-cluster-command", 
        #     cluster=admin_cluster,
        #     object_type="secrets",
        #     object_name=f"{tenant_config.name}-admin-kubeconfig",
        #     object_namespace=tenant_config.namespace,
        #     json_path=".data.admin\\.conf",
        # )
        # user_data.add_commands(f"base64 -d {tcp_kubeconfig} > {tenant_config.name}.kubeconfig")

        # Actually join nodes to the tcp
        # join_cluster_command = f"sudo $(kubeadm --kubeconfig={tenant_config.name}.kubeconfig token create --print-join-command)"
        # user_data.add_commands(join_cluster_command)

        # # Create the tenant's autoscaling group
        # asg = autoscaling.AutoScalingGroup(
        #     self,
        #     f"{tenant_config.name}-autoscaling-group",
        #     vpc=admin_cluster.vpc,
        #     machine_image=ec2.MachineImage.generic_linux({
        #         "eu-south-1": "ami-01fa20c124ed41944",
        #     }),
        #     user_data=Fn.base64(user_data.render()),
        # )
        # admin_cluster.connect_auto_scaling_group_capacity(asg)



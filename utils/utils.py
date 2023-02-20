import yaml
from typing import List
from os import listdir

class TenantConfig():

    name: str
    namespace: str
    domain: str
    version: str
    port: int
    proxy_port: int
    pod_cidr: str
    svc_cidr: str
    dns_service: str

    def __init__(self, name: str, namespace: str, domain: str, version: str, port: int, proxy_port: int, pod_cidr: str, svc_cidr: str, dns_service: str) -> None:
        self.name = name
        self.namespace = namespace
        self.domain = domain
        self.version = version
        self.port = port
        self.proxy_port = proxy_port
        self.pod_cidr = pod_cidr
        self.svc_cidr = svc_cidr
        self.dns_service = dns_service

    @staticmethod
    def load_from_file(file_path: str):
        tenant_config = None
        with open(file_path, 'r') as f:
            try:
                tenant_config = TenantConfig(**yaml.safe_load(f))
            except yaml.YAMLError as exc:
                print(f"can't load tenant config from `{file_path}`")

        return tenant_config

def load_tenants_config(basedir: str) -> List[TenantConfig]:
    return [ TenantConfig.load_from_file("/".join([basedir, tenant_config_file])) for tenant_config_file in listdir(basedir) ]

import re


def on_event(event, context):
    print(event)
    request_type = event['RequestType']
    if request_type == 'Create':
        return extract_oidc_id(event)
    if request_type == 'Update':
        return extract_oidc_id(event)
    if request_type == 'Delete':
        return
    raise Exception("Invalid request type: %s" % request_type)


def extract_oidc_id(event):
    props = event["ResourceProperties"]
    print("create new resource with props %s" % props)

    if arn := props["oidcProviderArn"]:
        oidc_provider_id = get_oidc_provider_id_from_arn(arn)
    else:
        raise Exception(
            "could not find `{oidcProviderArn}` in props `{props}`")

    return {'Data': { 'Id': oidc_provider_id } }


def get_oidc_provider_id_from_arn(arn: str) -> str:
    if groups := re.search(r'^arn:aws:iam::\d{12}:oidc-provider\/(.*)$', arn).groups():
        return groups[0]
    else:
        raise Exception(f"Failed to parse oidc provider arn `{arn}`")

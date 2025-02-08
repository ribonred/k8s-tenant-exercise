import kopf

@kopf.on.create('tenants')
def create_fn(spec, name, meta, status, **kwargs):
    print(f'Resource {name} was created and status is {status} \n with spec {spec} \n with meta {meta} \n with kwargs {kwargs}')
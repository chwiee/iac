from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import boto3

app = FastAPI()

session = boto3.Session()
client = session.client('route53')

class HostedZoneRequest(BaseModel):
    hosted_zone_id: str
    balancer_dns: str
    new_dns: str
    region: str
    resource_type: str

class CreateRecordRequest(BaseModel):
    ttl: int = 5

ELB_HOSTED_ZONE_IDS = {
    'us-east-1': {
        'ALB': 'Z35SXDOTRQ7X7K',
        'NLB': 'Z26RNL4JYFTOTI'
    },
    'us-west-2': {
        'ALB': 'Z1H1FL5HABSF5',
        'NLB': 'Z24FKFUX50B4VW'
    },
    'us-west-1': {
        'ALB': 'Z368ELLRRE2KJ0',
        'NLB': 'Z1M58G0W56PQJA'
    },
    'eu-west-1': {
        'ALB': 'Z32O12XQLNTSW2',
        'NLB': 'Z2IFOLAFXWLO4F'
    },
    'ap-southeast-1': {
        'ALB': 'Z1LMS91P8CMLE5',
        'NLB': 'ZKVM4W9LS7TM'
    },
    'ap-northeast-1': {
        'ALB': 'Z14GRHDCWA56QT',
        'NLB': 'Z31USIVHYNEOWT'
    },
    'ap-southeast-2': {
        'ALB': 'Z1GM3OXH4ZPM65',
        'NLB': 'ZTBHRN1DRG5OI'
    },
    'sa-east-1': {
        'ALB': 'Z2P70J7HTTTPLU',
        'NLB': 'Z3Q77PNBQS71R4'
    },
}

@app.get("/")
def read_root():
    return {"message": "API do Route 53 esta funcionando!"}

@app.get("/hosted-zones")
def list_hosted_zones():
    response = client.list_hosted_zones()
    hosted_zones = [
        {"Name": zone['Name'], "ID": zone['Id'].split('/')[-1]}
        for zone in response['HostedZones']
    ]
    return {"HostedZones": hosted_zones}

@app.post("/create-record")
def create_record(request: HostedZoneRequest, record: CreateRecordRequest):
    if request.resource_type not in ['ALB', 'NLB']:
        raise HTTPException(status_code=400, detail="Tipo de recurso invalido. Deve ser 'ALB' ou 'NLB'.")
    
    elb_hosted_zone_id = ELB_HOSTED_ZONE_IDS.get(request.region, {}).get(request.resource_type)
    
    if not elb_hosted_zone_id:
        raise HTTPException(status_code=400, detail=f"Regiao {request.region} ou tipo de recurso {request.resource_type} nao encontrado na lista de Hosted Zone IDs do ELB.")

    try:
        response = client.change_resource_record_sets(
            HostedZoneId=request.hosted_zone_id,
            ChangeBatch={
                'Comment': 'Criando um novo registro DNS para o balancer',
                'Changes': [
                    {
                        'Action': 'CREATE',
                        'ResourceRecordSet': {
                            'Name': request.new_dns,
                            'Type': 'A',
                            'TTL': record.ttl,
                            'ResourceRecords': [
                                {'Value': request.balancer_dns}
                            ]
                        }
                    }
                ]
            }
        )
        return {"message": f"Registro DNS {request.new_dns} criado com sucesso, apontando para {request.balancer_dns}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

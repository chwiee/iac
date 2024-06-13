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

class CreateRecordRequest(BaseModel):
    ttl: int = 5

ELB_HOSTED_ZONE_IDS = {
    'us-east-1': 'Z35SXDOTRQ7X7K',
    'us-west-2': 'Z1H1FL5HABSF5',
    'us-west-1': 'Z368ELLRRE2KJ0',
    'eu-west-1': 'Z32O12XQLNTSW2',
    'ap-southeast-1': 'Z1LMS91P8CMLE5',
    'ap-northeast-1': 'Z14GRHDCWA56QT',
    'ap-southeast-2': 'Z1GM3OXH4ZPM65',
    'sa-east-1': 'Z2P70J7HTTTPLU',
}

@app.get("/")
def read_root():
    return {"message": "API do Route 53 está funcionando!"}

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
    elb_hosted_zone_id = ELB_HOSTED_ZONE_IDS.get(request.region)
    
    if not elb_hosted_zone_id:
        raise HTTPException(status_code=400, detail=f"Região {request.region} não encontrada na lista de Hosted Zone IDs do ELB.")

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

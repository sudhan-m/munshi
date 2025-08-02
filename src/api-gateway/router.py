from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
import httpx
import os
from typing import Dict, Any
from .middleware import require_auth, get_user_from_token, auth_middleware
from dotenv import load_dotenv

load_dotenv()

class ServiceRegistry:
    def __init__(self):
        self.services = {
            "auth": os.getenv("AUTH_SERVICE_URL", "http://localhost:8001"),
        }
    
    def get_service_url(self, service_name: str) -> str:
        if service_name not in self.services:
            raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
        return self.services[service_name]
    
    def register_service(self, name: str, url: str):
        self.services[name] = url
    
    def unregister_service(self, name: str):
        if name in self.services:
            del self.services[name]

service_registry = ServiceRegistry()

def create_gateway_router() -> APIRouter:
    router = APIRouter()
    
    @router.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def proxy_auth_service(path: str, request: Request):
        """Proxy requests to auth service (no auth required for login/register)"""
        auth_url = service_registry.get_service_url("auth")
        
        async with httpx.AsyncClient() as client:
            url = f"{auth_url}/auth/{path}"
            
            headers = dict(request.headers)
            headers.pop("host", None)
            
            body = await request.body()
            
            try:
                response = await client.request(
                    method=request.method,
                    url=url,
                    headers=headers,
                    content=body,
                    params=request.query_params
                )
                
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
            except httpx.RequestError as e:
                raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")
    
    @router.api_route("/protected/{service_name}/{path:path}", 
                     methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def proxy_protected_service(
        service_name: str, 
        path: str, 
        request: Request,
        token: str = Depends(require_auth),
        user: dict = Depends(get_user_from_token)
    ):
        """Proxy requests to protected services (requires authentication)"""
        service_url = service_registry.get_service_url(service_name)
        
        async with httpx.AsyncClient() as client:
            url = f"{service_url}/{path}"
            
            headers = dict(request.headers)
            headers.pop("host", None)
            headers["X-User-Email"] = user["email"]
            headers["X-User-ID"] = str(user["id"])
            
            body = await request.body()
            
            try:
                response = await client.request(
                    method=request.method,
                    url=url,
                    headers=headers,
                    content=body,
                    params=request.query_params
                )
                
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
            except httpx.RequestError as e:
                raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")
    
    @router.get("/services")
    async def list_services(token: str = Depends(require_auth)):
        """List all registered services"""
        return {"services": list(service_registry.services.keys())}
    
    @router.post("/services/{service_name}")
    async def register_service(
        service_name: str, 
        service_data: Dict[str, str],
        token: str = Depends(require_auth)
    ):
        """Register a new service"""
        service_registry.register_service(service_name, service_data["url"])
        return {"message": f"Service {service_name} registered successfully"}
    
    @router.delete("/services/{service_name}")
    async def unregister_service(service_name: str, token: str = Depends(require_auth)):
        """Unregister a service"""
        service_registry.unregister_service(service_name)
        return {"message": f"Service {service_name} unregistered successfully"}
    
    return router
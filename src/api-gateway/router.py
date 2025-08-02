from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
import httpx
import os
import ssl
from typing import Dict, Any
from .middleware import require_auth, get_user_from_token, auth_middleware
from dotenv import load_dotenv

load_dotenv()

class ServiceRegistry:
    def __init__(self):
        self.services = {
            "auth": os.getenv("AUTH_SERVICE_URL", "https://auth-service:8001"),
        }
        # Setup mTLS configuration
        self.ssl_context = self._create_ssl_context()
    
    def _create_ssl_context(self):
        """Create SSL context for mTLS communication with auth service"""
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        
        # Load CA certificate
        ca_cert_path = os.getenv("CA_CERT_PATH", "/etc/caddy/certs/ca.crt")
        if os.path.exists(ca_cert_path):
            context.load_verify_locations(ca_cert_path)
        
        # Load client certificate and key for mTLS
        client_cert_path = os.getenv("CLIENT_CERT_PATH", "/etc/caddy/certs/gateway.crt")
        client_key_path = os.getenv("CLIENT_KEY_PATH", "/etc/caddy/certs/gateway.key")
        
        if os.path.exists(client_cert_path) and os.path.exists(client_key_path):
            context.load_cert_chain(client_cert_path, client_key_path)
        
        # In development, you might want to disable certificate verification
        if os.getenv("ENVIRONMENT") == "development":
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        
        return context
    
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
        
        # Create httpx client with mTLS support
        async with httpx.AsyncClient(verify=service_registry.ssl_context) as client:
            url = f"{auth_url}/auth/{path}"
            
            headers = dict(request.headers)
            headers.pop("host", None)
            headers["X-Gateway-ID"] = "api-gateway"
            headers["X-Request-ID"] = getattr(request.state, "request_id", "unknown")
            
            body = await request.body()
            
            try:
                response = await client.request(
                    method=request.method,
                    url=url,
                    headers=headers,
                    content=body,
                    params=request.query_params,
                    timeout=30.0
                )
                
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
            except httpx.RequestError as e:
                raise HTTPException(status_code=503, detail=f"Auth service unavailable: {str(e)}")
            except httpx.TimeoutException:
                raise HTTPException(status_code=504, detail="Auth service timeout")
    
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
        
        # Use mTLS for auth service, regular HTTPS for others
        ssl_context = service_registry.ssl_context if service_name == "auth" else True
        
        async with httpx.AsyncClient(verify=ssl_context) as client:
            url = f"{service_url}/{path}"
            
            headers = dict(request.headers)
            headers.pop("host", None)
            headers["X-User-Email"] = user["email"]
            headers["X-User-ID"] = str(user["id"])
            headers["X-Gateway-ID"] = "api-gateway"
            headers["X-Request-ID"] = getattr(request.state, "request_id", "unknown")
            
            body = await request.body()
            
            try:
                response = await client.request(
                    method=request.method,
                    url=url,
                    headers=headers,
                    content=body,
                    params=request.query_params,
                    timeout=30.0
                )
                
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
            except httpx.RequestError as e:
                raise HTTPException(status_code=503, detail=f"Service {service_name} unavailable: {str(e)}")
            except httpx.TimeoutException:
                raise HTTPException(status_code=504, detail=f"Service {service_name} timeout")
    
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
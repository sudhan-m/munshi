from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
import httpx
import os
import logging
from typing import Dict, Any
from middleware import require_auth, get_user_from_token, auth_middleware
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class ServiceRegistry:
    def __init__(self):
        self.services = {
            # Use Linkerd service discovery - automatic mTLS
            "auth": os.getenv("AUTH_SERVICE_URL", "http://auth-service.munshi.svc.cluster.local:8001"),
        }
        # Linkerd handles mTLS automatically - no need for custom SSL context
        self.client_config = self._create_client_config()
    
    def _create_client_config(self):
        """Create HTTP client configuration optimized for Linkerd"""
        return {
            "timeout": httpx.Timeout(
                connect=5.0,
                read=30.0,
                write=10.0,
                pool=5.0
            ),
            "limits": httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
                keepalive_expiry=30.0
            ),
            # Trust Linkerd's automatic mTLS
            "verify": True,
            "headers": {
                "User-Agent": "munshi-api-gateway/1.0",
                "X-Service-Mesh": "linkerd"
            }
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
        
        # Create httpx client optimized for Linkerd
        async with httpx.AsyncClient(**service_registry.client_config) as client:
            url = f"{auth_url}/auth/{path}"
            
            headers = dict(request.headers)
            headers.pop("host", None)
            # Linkerd service identity headers
            headers["X-Gateway-ID"] = "api-gateway"
            headers["X-Request-ID"] = getattr(request.state, "request_id", "unknown")
            headers["X-Linkerd-Service-Name"] = "api-gateway"
            headers["X-Linkerd-Destination"] = "auth-service"
            
            body = await request.body()
            
            try:
                logger.debug(f"Proxying {request.method} {url} via Linkerd")
                response = await client.request(
                    method=request.method,
                    url=url,
                    headers=headers,
                    content=body,
                    params=request.query_params
                )
                
                # Add Linkerd observability headers
                response_headers = dict(response.headers)
                response_headers["X-Linkerd-Proxy"] = "true"
                
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=response_headers
                )
            except httpx.ConnectError as e:
                logger.error(f"Connection error to auth service via Linkerd: {str(e)}")
                raise HTTPException(status_code=503, detail="Auth service unavailable")
            except httpx.TimeoutException as e:
                logger.error(f"Timeout calling auth service via Linkerd: {str(e)}")
                raise HTTPException(status_code=504, detail="Auth service timeout")
            except httpx.RequestError as e:
                logger.error(f"Request error to auth service via Linkerd: {str(e)}")
                raise HTTPException(status_code=503, detail="Auth service error")
    
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
        
        # Use Linkerd for all service communication
        async with httpx.AsyncClient(**service_registry.client_config) as client:
            url = f"{service_url}/{path}"
            
            headers = dict(request.headers)
            headers.pop("host", None)
            # Add user context for downstream services
            headers["X-User-Email"] = user["email"]
            headers["X-User-ID"] = str(user["id"])
            headers["X-Gateway-ID"] = "api-gateway"
            headers["X-Request-ID"] = getattr(request.state, "request_id", "unknown")
            # Linkerd service mesh headers
            headers["X-Linkerd-Service-Name"] = "api-gateway"
            headers["X-Linkerd-Destination"] = service_name
            headers["X-Authenticated-User"] = user["email"]
            
            body = await request.body()
            
            try:
                logger.debug(f"Proxying authenticated {request.method} {url} via Linkerd for user {user['email']}")
                response = await client.request(
                    method=request.method,
                    url=url,
                    headers=headers,
                    content=body,
                    params=request.query_params
                )
                
                # Add Linkerd observability headers
                response_headers = dict(response.headers)
                response_headers["X-Linkerd-Proxy"] = "true"
                response_headers["X-Authenticated-Request"] = "true"
                
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=response_headers
                )
            except httpx.ConnectError as e:
                logger.error(f"Connection error to {service_name} via Linkerd: {str(e)}")
                raise HTTPException(status_code=503, detail=f"Service {service_name} unavailable")
            except httpx.TimeoutException as e:
                logger.error(f"Timeout calling {service_name} via Linkerd: {str(e)}")
                raise HTTPException(status_code=504, detail=f"Service {service_name} timeout")
            except httpx.RequestError as e:
                logger.error(f"Request error to {service_name} via Linkerd: {str(e)}")
                raise HTTPException(status_code=503, detail=f"Service {service_name} error")
    
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
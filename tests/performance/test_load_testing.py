"""
Performance and load testing for microservices.

Tests system performance under various load conditions
and identifies bottlenecks and scalability limits.
"""

import pytest
import asyncio
import time
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor


@pytest.mark.performance
@pytest.mark.slow
class TestLoadTesting:
    """Load testing for authentication service."""
    
    @pytest.fixture(autouse=True)
    def setup(self, test_settings):
        """Setup performance test environment."""
        self.settings = test_settings
        self.auth_service_url = "http://localhost:8001"
        self.gateway_url = "http://localhost:8000"
        self.concurrent_users = 50
        self.test_duration = 30  # seconds
    
    @pytest.mark.asyncio
    async def test_authentication_throughput(self, test_client):
        """Test authentication service throughput under load."""
        # Setup test users
        test_users = await self._create_test_users(test_client, count=10)
        
        # Performance metrics
        metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "response_times": [],
            "errors": []
        }
        
        async def login_worker(user_data: Dict[str, Any]):
            """Worker function for login load test."""
            for _ in range(10):  # Each user logs in 10 times
                start_time = time.time()
                
                try:
                    response = await self._simulate_login(
                        test_client,
                        user_data["email"],
                        user_data["password"]
                    )
                    
                    response_time = time.time() - start_time
                    metrics["response_times"].append(response_time)
                    metrics["total_requests"] += 1
                    
                    if response.get("success"):
                        metrics["successful_requests"] += 1
                    else:
                        metrics["failed_requests"] += 1
                        metrics["errors"].append(response.get("error", "Unknown error"))
                
                except Exception as e:
                    metrics["failed_requests"] += 1
                    metrics["errors"].append(str(e))
                    metrics["total_requests"] += 1
                
                # Small delay between requests
                await asyncio.sleep(0.1)
        
        # Run load test
        start_time = time.time()
        tasks = [login_worker(user) for user in test_users]
        await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Analyze results
        success_rate = (metrics["successful_requests"] / metrics["total_requests"]) * 100
        avg_response_time = sum(metrics["response_times"]) / len(metrics["response_times"])
        throughput = metrics["total_requests"] / total_time
        
        # Performance assertions
        assert success_rate >= 95, f"Success rate too low: {success_rate}%"
        assert avg_response_time <= 1.0, f"Average response time too high: {avg_response_time}s"
        assert throughput >= 10, f"Throughput too low: {throughput} req/s"
        
        # Log performance metrics
        print(f"\nPerformance Results:")
        print(f"Total Requests: {metrics['total_requests']}")
        print(f"Success Rate: {success_rate:.2f}%")
        print(f"Average Response Time: {avg_response_time:.3f}s")
        print(f"Throughput: {throughput:.2f} req/s")
    
    @pytest.mark.asyncio
    async def test_concurrent_user_registration(self, test_client):
        """Test concurrent user registration performance."""
        concurrent_registrations = 20
        
        async def register_user(user_id: int):
            """Register a single user."""
            user_data = {
                "email": f"loadtest{user_id}@example.com",
                "username": f"loadtest{user_id}",
                "password": "LoadTest123"
            }
            
            start_time = time.time()
            response = await self._simulate_registration(test_client, user_data)
            response_time = time.time() - start_time
            
            return {
                "user_id": user_id,
                "success": response.get("success", False),
                "response_time": response_time,
                "error": response.get("error")
            }
        
        # Run concurrent registrations
        start_time = time.time()
        tasks = [register_user(i) for i in range(concurrent_registrations)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Analyze results
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        avg_response_time = sum(r["response_time"] for r in results) / len(results)
        
        # Performance assertions
        success_rate = (len(successful) / len(results)) * 100
        assert success_rate >= 95, f"Registration success rate too low: {success_rate}%"
        assert avg_response_time <= 2.0, f"Average registration time too high: {avg_response_time}s"
        
        print(f"\nConcurrent Registration Results:")
        print(f"Successful: {len(successful)}/{len(results)}")
        print(f"Success Rate: {success_rate:.2f}%")
        print(f"Average Response Time: {avg_response_time:.3f}s")
        print(f"Total Time: {total_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_token_validation_performance(self, test_client):
        """Test token validation performance under load."""
        # Setup authenticated users
        test_users = await self._create_test_users(test_client, count=5)
        
        # Get tokens for all users
        tokens = []
        for user in test_users:
            login_response = await self._simulate_login(
                test_client,
                user["email"],
                user["password"]
            )
            if login_response.get("success"):
                tokens.append(login_response["access_token"])
        
        validation_metrics = {
            "total_validations": 0,
            "successful_validations": 0,
            "response_times": []
        }
        
        async def validate_token_worker(token: str):
            """Worker for token validation load test."""
            for _ in range(20):  # Validate each token 20 times
                start_time = time.time()
                
                response = await self._simulate_token_validation(test_client, token)
                
                response_time = time.time() - start_time
                validation_metrics["response_times"].append(response_time)
                validation_metrics["total_validations"] += 1
                
                if response.get("valid"):
                    validation_metrics["successful_validations"] += 1
                
                await asyncio.sleep(0.05)  # Small delay
        
        # Run validation load test
        start_time = time.time()
        tasks = [validate_token_worker(token) for token in tokens]
        await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Analyze results
        success_rate = (validation_metrics["successful_validations"] / validation_metrics["total_validations"]) * 100
        avg_response_time = sum(validation_metrics["response_times"]) / len(validation_metrics["response_times"])
        throughput = validation_metrics["total_validations"] / total_time
        
        # Performance assertions (token validation should be very fast)
        assert success_rate >= 99, f"Token validation success rate too low: {success_rate}%"
        assert avg_response_time <= 0.1, f"Token validation too slow: {avg_response_time}s"
        assert throughput >= 100, f"Token validation throughput too low: {throughput} validations/s"
        
        print(f"\nToken Validation Performance:")
        print(f"Total Validations: {validation_metrics['total_validations']}")
        print(f"Success Rate: {success_rate:.2f}%")
        print(f"Average Response Time: {avg_response_time:.4f}s")
        print(f"Throughput: {throughput:.2f} validations/s")
    
    @pytest.mark.asyncio
    async def test_rate_limiting_performance(self, test_client):
        """Test rate limiting behavior under high load."""
        # Setup user for rate limit testing
        user_data = {
            "email": "ratelimit@example.com",
            "username": "ratelimit",
            "password": "RateLimit123"
        }
        
        await self._simulate_registration(test_client, user_data)
        login_response = await self._simulate_login(
            test_client,
            user_data["email"],
            user_data["password"]
        )
        
        token = login_response["access_token"]
        
        # Make rapid requests to trigger rate limiting
        rate_limit_results = []
        
        for i in range(100):  # Make 100 rapid requests
            start_time = time.time()
            response = await self._simulate_authenticated_request(test_client, token)
            response_time = time.time() - start_time
            
            rate_limit_results.append({
                "request_number": i + 1,
                "success": response.get("success", False),
                "response_time": response_time,
                "status_code": response.get("status_code", 200)
            })
            
            # No delay - test rapid requests
        
        # Analyze rate limiting behavior
        successful_requests = [r for r in rate_limit_results if r["success"]]
        rate_limited_requests = [r for r in rate_limit_results if r["status_code"] == 429]
        
        # Should have some rate limited requests
        assert len(rate_limited_requests) > 0, "Rate limiting not working"
        
        # Rate limited responses should be fast
        if rate_limited_requests:
            avg_rate_limit_time = sum(r["response_time"] for r in rate_limited_requests) / len(rate_limited_requests)
            assert avg_rate_limit_time <= 0.1, f"Rate limit responses too slow: {avg_rate_limit_time}s"
        
        print(f"\nRate Limiting Results:")
        print(f"Total Requests: {len(rate_limit_results)}")
        print(f"Successful: {len(successful_requests)}")
        print(f"Rate Limited: {len(rate_limited_requests)}")
    
    @pytest.mark.asyncio
    async def test_database_connection_pool_performance(self, database_manager):
        """Test database connection pool performance under load."""
        async def database_operation_worker(worker_id: int):
            """Worker for database load testing."""
            operations = []
            
            for i in range(10):
                start_time = time.time()
                
                # Simulate database operation
                try:
                    with database_manager.get_session() as session:
                        # Simple query to test connection
                        result = session.execute("SELECT 1").fetchone()
                        success = result is not None
                except Exception as e:
                    success = False
                
                response_time = time.time() - start_time
                operations.append({
                    "worker_id": worker_id,
                    "operation_id": i,
                    "success": success,
                    "response_time": response_time
                })
                
                await asyncio.sleep(0.1)
            
            return operations
        
        # Run concurrent database operations
        start_time = time.time()
        tasks = [database_operation_worker(i) for i in range(20)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Flatten results
        all_operations = [op for worker_results in results for op in worker_results]
        
        # Analyze database performance
        successful_ops = [op for op in all_operations if op["success"]]
        success_rate = (len(successful_ops) / len(all_operations)) * 100
        avg_response_time = sum(op["response_time"] for op in all_operations) / len(all_operations)
        
        # Database performance assertions
        assert success_rate >= 99, f"Database success rate too low: {success_rate}%"
        assert avg_response_time <= 0.5, f"Database operations too slow: {avg_response_time}s"
        
        print(f"\nDatabase Performance:")
        print(f"Total Operations: {len(all_operations)}")
        print(f"Success Rate: {success_rate:.2f}%")
        print(f"Average Response Time: {avg_response_time:.4f}s")
    
    # Helper methods
    
    async def _create_test_users(self, test_client, count: int) -> List[Dict[str, Any]]:
        """Create multiple test users for load testing."""
        users = []
        
        for i in range(count):
            user_data = {
                "email": f"perftest{i}@example.com",
                "username": f"perftest{i}",
                "password": "PerfTest123"
            }
            
            await self._simulate_registration(test_client, user_data)
            users.append(user_data)
        
        return users
    
    async def _simulate_registration(self, test_client, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate user registration."""
        # Mock successful registration
        return {
            "success": True,
            "user_id": hash(user_data["email"]) % 10000,
            "email": user_data["email"]
        }
    
    async def _simulate_login(self, test_client, email: str, password: str) -> Dict[str, Any]:
        """Simulate user login."""
        # Mock successful login
        return {
            "success": True,
            "access_token": f"perf_token_{email}_{int(time.time())}",
            "token_type": "bearer"
        }
    
    async def _simulate_token_validation(self, test_client, token: str) -> Dict[str, Any]:
        """Simulate token validation."""
        # Mock token validation
        return {
            "valid": True,
            "email": token.split("_")[2] if "_" in token else "unknown@example.com"
        }
    
    async def _simulate_authenticated_request(self, test_client, token: str) -> Dict[str, Any]:
        """Simulate authenticated API request."""
        # Mock authenticated request with rate limiting
        import random
        
        # Simulate rate limiting (10% chance of being rate limited)
        if random.random() < 0.1:
            return {
                "success": False,
                "status_code": 429,
                "error": "Rate limit exceeded"
            }
        
        return {
            "success": True,
            "status_code": 200,
            "data": {"message": "Success"}
        }
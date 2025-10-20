#!/usr/bin/env python3
"""
Comprehensive Test Suite for AI RFP Assistant
This consolidates all testing functionality into a single, comprehensive test suite.
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

try:
    import requests
    import aiohttp
except ImportError:
    print("Please install required dependencies: pip install requests aiohttp")
    sys.exit(1)

# Add project root to path
sys.path.append(os.path.dirname(__file__))

# Import our modules
from services.s3_client import s3_client
from services.dynamodb_client import dynamodb_client
from agents.orchestrator_agent import OrchestratorAgent
from config.model_config import model_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_results.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TestResult:
    """Container for test results."""
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.passed = False
        self.error = None
        self.duration = 0.0
        self.details = {}
        self.timestamp = datetime.now()

class TestSuite:
    """Comprehensive test suite for the AI RFP Assistant."""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.session_id = str(uuid.uuid4())
        self.test_start_time = datetime.now()
        
    def add_result(self, result: TestResult):
        """Add a test result."""
        self.results.append(result)
        status = "✅ PASS" if result.passed else "❌ FAIL"
        logger.info(f"{status} {result.test_name} ({result.duration:.2f}s)")
        if result.error:
            logger.error(f"   Error: {result.error}")

    async def test_service_connectivity(self) -> TestResult:
        """Test if all required services are running."""
        result = TestResult("Service Connectivity")
        start_time = time.time()
        
        try:
            services = {
                "Ollama": "http://localhost:11434/api/tags",
                "DynamoDB Local": "http://localhost:8000",
                "MinIO": "http://localhost:9000/minio/health/live",
                "FastAPI Backend": "http://localhost:8001/health",
                "Chainlit App": "http://localhost:8081"
            }
            
            service_status = {}
            async with aiohttp.ClientSession() as session:
                for service_name, url in services.items():
                    try:
                        async with session.get(url, timeout=5) as response:
                            if response.status in [200, 400]:  # 400 is OK for DynamoDB
                                service_status[service_name] = "✅ Running"
                            else:
                                service_status[service_name] = f"❌ Status {response.status}"
                    except Exception as e:
                        service_status[service_name] = f"❌ Error: {str(e)[:50]}"
            
            result.details = service_status
            result.passed = all("✅" in status for status in service_status.values())
            
        except Exception as e:
            result.error = str(e)
            result.passed = False
        
        result.duration = time.time() - start_time
        return result

    async def test_model_configuration(self) -> TestResult:
        """Test model configuration loading."""
        result = TestResult("Model Configuration")
        start_time = time.time()
        
        try:
            model = model_config.get_model()
            result.details = {
                "provider": model_config.model_provider,
                "model_id": model_config.model_id,
                "model_object": str(type(model))
            }
            result.passed = model is not None
            
        except Exception as e:
            result.error = str(e)
            result.passed = False
        
        result.duration = time.time() - start_time
        return result

    async def test_storage_services(self) -> TestResult:
        """Test S3 and DynamoDB connectivity."""
        result = TestResult("Storage Services")
        start_time = time.time()
        
        try:
            # Test S3/MinIO
            s3_test_data = f"test_data_{self.session_id}".encode('utf-8')
            test_key = f"test/{self.session_id}/test_file.txt"
            
            # Upload test file
            upload_success = s3_client.upload_file_object(
                file_data=s3_test_data,
                object_key=test_key,
                content_type="text/plain",
                metadata={"test": "true", "session_id": self.session_id}
            )
            
            # Download test file
            download_data = s3_client.download_file_object(test_key)
            download_success = download_data == s3_test_data
            
            # Test DynamoDB
            test_data = {
                "test": True,
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat()
            }
            
            save_success = dynamodb_client.save_session_data(self.session_id, test_data)
            retrieved_data = dynamodb_client.get_session_data(self.session_id)
            retrieve_success = retrieved_data is not None
            
            result.details = {
                "s3_upload": upload_success,
                "s3_download": download_success,
                "dynamodb_save": save_success,
                "dynamodb_retrieve": retrieve_success
            }
            result.passed = all([upload_success, download_success, save_success, retrieve_success])
            
        except Exception as e:
            result.error = str(e)
            result.passed = False
        
        result.duration = time.time() - start_time
        return result

    async def test_orchestrator_agent(self) -> TestResult:
        """Test orchestrator agent functionality."""
        result = TestResult("Orchestrator Agent")
        start_time = time.time()
        
        try:
            orchestrator = OrchestratorAgent()
            
            # Test routing
            test_queries = [
                "Generate a technical solution for cloud migration",
                "Create a compliance checklist",
                "Draft financial projections",
                "Analyze requirements and create win themes"
            ]
            
            routing_results = {}
            for query in test_queries:
                try:
                    routing = await orchestrator.route_task(query)
                    routing_results[query[:30]] = routing
                except Exception as e:
                    routing_results[query[:30]] = f"Error: {str(e)}"
            
            # Test full orchestration with a simple query
            orchestration_result = await orchestrator.run("Test query for system validation")
            
            result.details = {
                "routing_tests": routing_results,
                "orchestration_success": isinstance(orchestration_result, dict),
                "result_keys": list(orchestration_result.keys()) if isinstance(orchestration_result, dict) else []
            }
            result.passed = isinstance(orchestration_result, dict) and "section" in orchestration_result
            
        except Exception as e:
            result.error = str(e)
            result.passed = False
        
        result.duration = time.time() - start_time
        return result

    async def test_api_endpoints(self) -> TestResult:
        """Test FastAPI backend endpoints."""
        result = TestResult("API Endpoints")
        start_time = time.time()
        
        try:
            base_url = "http://localhost:8001"
            
            # Test health endpoint
            health_response = requests.get(f"{base_url}/health", timeout=5)
            health_ok = health_response.status_code == 200
            
            # Test session endpoints
            test_session_data = {"test": True, "timestamp": datetime.now().isoformat()}
            
            # Save session
            save_response = requests.post(
                f"{base_url}/session/{self.session_id}",
                json=test_session_data,
                timeout=5
            )
            save_ok = save_response.status_code == 200
            
            # Get session
            get_response = requests.get(f"{base_url}/session/{self.session_id}", timeout=5)
            get_ok = get_response.status_code == 200
            
            # Test content loading (if we have stored content)
            content_response = requests.post(
                f"{base_url}/load-content",
                json={"content_key": f"test/{self.session_id}/test_file.txt", "session_id": self.session_id},
                timeout=5
            )
            content_ok = content_response.status_code in [200, 404]  # 404 is OK if no content
            
            result.details = {
                "health_endpoint": health_ok,
                "save_session": save_ok,
                "get_session": get_ok,
                "load_content": content_ok
            }
            result.passed = all([health_ok, save_ok, get_ok, content_ok])
            
        except Exception as e:
            result.error = str(e)
            result.passed = False
        
        result.duration = time.time() - start_time
        return result

    async def test_canvas_functionality(self) -> TestResult:
        """Test canvas file serving and functionality."""
        result = TestResult("Canvas Functionality")
        start_time = time.time()
        
        try:
            # Test canvas HTML file
            canvas_html_path = "public/canvas.html"
            canvas_js_path = "public/canvas.js"
            
            html_exists = os.path.exists(canvas_html_path)
            js_exists = os.path.exists(canvas_js_path)
            
            # Test file serving through FastAPI
            canvas_response = requests.get("http://localhost:8001/canvas/canvas.html", timeout=5)
            canvas_served = canvas_response.status_code == 200
            
            result.details = {
                "html_file_exists": html_exists,
                "js_file_exists": js_exists,
                "canvas_served": canvas_served
            }
            result.passed = html_exists and js_exists and canvas_served
            
        except Exception as e:
            result.error = str(e)
            result.passed = False
        
        result.duration = time.time() - start_time
        return result

    async def test_end_to_end_workflow(self) -> TestResult:
        """Test complete end-to-end workflow."""
        result = TestResult("End-to-End Workflow")
        start_time = time.time()
        
        try:
            # Test with a sample RFP document if available
            test_doc_path = "test_rfp_document.md"
            has_test_doc = os.path.exists(test_doc_path)
            
            orchestrator = OrchestratorAgent()
            
            # Test different types of queries
            test_scenarios = [
                {
                    "query": "Analyze the requirements and create win themes",
                    "expected_agent": "StrategistAgent"
                },
                {
                    "query": "Design a technical solution architecture",
                    "expected_agent": "SolutionArchitectAgent"
                },
                {
                    "query": "Create a compliance checklist",
                    "expected_agent": "ComplianceAgent"
                }
            ]
            
            scenario_results = {}
            for scenario in test_scenarios:
                try:
                    workflow_result = await orchestrator.run(scenario["query"])
                    scenario_results[scenario["query"][:30]] = {
                        "success": isinstance(workflow_result, dict),
                        "agent": workflow_result.get("agent", "Unknown") if isinstance(workflow_result, dict) else "Error",
                        "has_output": bool(workflow_result.get("output", "")) if isinstance(workflow_result, dict) else False
                    }
                except Exception as e:
                    scenario_results[scenario["query"][:30]] = {"error": str(e)}
            
            result.details = {
                "test_document_available": has_test_doc,
                "scenario_results": scenario_results,
                "successful_scenarios": sum(1 for r in scenario_results.values() if r.get("success", False))
            }
            result.passed = any(r.get("success", False) for r in scenario_results.values())
            
        except Exception as e:
            result.error = str(e)
            result.passed = False
        
        result.duration = time.time() - start_time
        return result

    async def test_import_resilience(self) -> TestResult:
        """Test import resilience and fallback mechanisms."""
        result = TestResult("Import Resilience")
        start_time = time.time()
        
        try:
            import_tests = {}
            
            # Test main module imports
            try:
                import main
                import_tests["main_module"] = "✅ Success"
            except Exception as e:
                import_tests["main_module"] = f"❌ Failed: {str(e)[:100]}"
            
            # Test orchestrator imports
            try:
                from agents.orchestrator_agent import OrchestratorAgent
                import_tests["orchestrator"] = "✅ Success"
            except Exception as e:
                import_tests["orchestrator"] = f"❌ Failed: {str(e)[:100]}"
            
            # Test config imports
            try:
                from config.model_config import model_config
                import_tests["model_config"] = "✅ Success"
            except Exception as e:
                import_tests["model_config"] = f"❌ Failed: {str(e)[:100]}"
            
            # Test service imports
            try:
                from services.s3_client import s3_client
                from services.dynamodb_client import dynamodb_client
                import_tests["services"] = "✅ Success"
            except Exception as e:
                import_tests["services"] = f"❌ Failed: {str(e)[:100]}"
            
            # Test specialized agents
            agent_imports = {}
            try:
                from agents.specialized.content_agent import content_agent
                agent_imports["content_agent"] = "✅ Success"
            except Exception as e:
                agent_imports["content_agent"] = f"❌ Failed: {str(e)[:50]}"
            
            try:
                from agents.specialized.strategist_agent import strategist_agent
                agent_imports["strategist_agent"] = "✅ Success"
            except Exception as e:
                agent_imports["strategist_agent"] = f"❌ Failed: {str(e)[:50]}"
            
            result.details = {
                "core_imports": import_tests,
                "agent_imports": agent_imports,
                "successful_imports": sum(1 for v in import_tests.values() if "✅" in v),
                "total_imports": len(import_tests)
            }
            result.passed = len([v for v in import_tests.values() if "✅" in v]) >= 3  # At least 3 core imports should work
            
        except Exception as e:
            result.error = str(e)
            result.passed = False
        
        result.duration = time.time() - start_time
        return result

    async def test_file_structure(self) -> TestResult:
        """Test that all required files and directories exist."""
        result = TestResult("File Structure")
        start_time = time.time()
        
        try:
            required_files = [
                "main.py",
                "scripts/start.py",
                "scripts/setup.py",
                "testsuite.py",
                "fastapi_backend.py",
                "requirements.txt",
                "config.yaml",
                "docker-compose.yaml",
                "README.md"
            ]
            
            required_dirs = [
                "agents",
                "agents/specialized",
                "agents/functional",
                "config",
                "services",
                "utils",
                "public"
            ]
            
            file_results = {}
            for file_path in required_files:
                exists = os.path.exists(file_path)
                file_results[file_path] = "✅ Exists" if exists else "❌ Missing"
            
            dir_results = {}
            for dir_path in required_dirs:
                exists = os.path.exists(dir_path) and os.path.isdir(dir_path)
                dir_results[dir_path] = "✅ Exists" if exists else "❌ Missing"
            
            missing_files = [f for f, status in file_results.items() if "❌" in status]
            missing_dirs = [d for d, status in dir_results.items() if "❌" in status]
            
            result.details = {
                "files": file_results,
                "directories": dir_results,
                "missing_files": missing_files,
                "missing_directories": missing_dirs,
                "files_present": len(required_files) - len(missing_files),
                "dirs_present": len(required_dirs) - len(missing_dirs)
            }
            result.passed = len(missing_files) == 0 and len(missing_dirs) == 0
            
        except Exception as e:
            result.error = str(e)
            result.passed = False
        
        result.duration = time.time() - start_time
        return result

    async def test_configuration_validation(self) -> TestResult:
        """Test configuration files and environment setup."""
        result = TestResult("Configuration Validation")
        start_time = time.time()
        
        try:
            config_tests = {}
            
            # Test config.yaml
            try:
                import yaml
                with open("config.yaml", "r") as f:
                    config_data = yaml.safe_load(f)
                config_tests["config_yaml"] = "✅ Valid YAML"
            except Exception as e:
                config_tests["config_yaml"] = f"❌ Invalid: {str(e)[:50]}"
            
            # Test requirements.txt
            try:
                with open("requirements.txt", "r") as f:
                    requirements = f.read()
                if requirements.strip():
                    config_tests["requirements_txt"] = "✅ Has dependencies"
                else:
                    config_tests["requirements_txt"] = "❌ Empty"
            except Exception as e:
                config_tests["requirements_txt"] = f"❌ Error: {str(e)[:50]}"
            
            # Test docker-compose.yaml
            try:
                with open("docker-compose.yaml", "r") as f:
                    docker_config = yaml.safe_load(f)
                if "services" in docker_config:
                    config_tests["docker_compose"] = "✅ Valid Docker config"
                else:
                    config_tests["docker_compose"] = "❌ Missing services"
            except Exception as e:
                config_tests["docker_compose"] = f"❌ Invalid: {str(e)[:50]}"
            
            # Test environment variables
            env_vars = ["MODEL_PROVIDER", "MODEL_ID", "OLLAMA_HOST"]
            env_results = {}
            for var in env_vars:
                value = os.getenv(var)
                env_results[var] = f"✅ {value}" if value else "⚠️ Not set"
            
            result.details = {
                "config_files": config_tests,
                "environment_variables": env_results,
                "valid_configs": len([v for v in config_tests.values() if "✅" in v])
            }
            result.passed = len([v for v in config_tests.values() if "✅" in v]) >= 2
            
        except Exception as e:
            result.error = str(e)
            result.passed = False
        
        result.duration = time.time() - start_time
        return result

    async def run_all_tests(self) -> Dict:
        """Run all tests and return comprehensive results."""
        logger.info("🚀 Starting comprehensive test suite...")
        logger.info(f"Session ID: {self.session_id}")
        
        test_methods = [
            self.test_service_connectivity,
            self.test_model_configuration,
            self.test_storage_services,
            self.test_orchestrator_agent,
            self.test_api_endpoints,
            self.test_canvas_functionality,
            self.test_end_to_end_workflow,
            self.test_import_resilience,
            self.test_file_structure,
            self.test_configuration_validation
        ]
        
        for test_method in test_methods:
            try:
                result = await test_method()
                self.add_result(result)
            except Exception as e:
                error_result = TestResult(test_method.__name__.replace("test_", "").replace("_", " ").title())
                error_result.error = str(e)
                error_result.passed = False
                self.add_result(error_result)
        
        # Generate summary
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        total_duration = sum(r.duration for r in self.results)
        
        summary = {
            "session_id": self.session_id,
            "test_start_time": self.test_start_time.isoformat(),
            "test_end_time": datetime.now().isoformat(),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%",
            "total_duration": f"{total_duration:.2f}s",
            "results": [
                {
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "duration": f"{r.duration:.2f}s",
                    "error": r.error,
                    "details": r.details
                }
                for r in self.results
            ]
        }
        
        # Save results to file
        with open("test_suite_results.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        logger.info("="*60)
        logger.info("📊 TEST SUITE SUMMARY")
        logger.info("="*60)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success Rate: {summary['success_rate']}")
        logger.info(f"Total Duration: {summary['total_duration']}")
        logger.info("="*60)
        
        return summary

async def main():
    """Main test runner."""
    test_suite = TestSuite()
    results = await test_suite.run_all_tests()
    
    # Exit with appropriate code
    if results["failed_tests"] == 0:
        logger.info("🎉 All tests passed!")
        sys.exit(0)
    else:
        logger.error(f"❌ {results['failed_tests']} tests failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

"""
Comprehensive debugging endpoint for /api/chat failures.

This endpoint captures:
1. Full request body logging
2. Environment variable validation
3. Python API connection testing
4. Module import testing
5. Supabase connectivity checks
6. Anthropic API key validation
7. Vercel AI Gateway connectivity
8. Request/response flow tracing

Deployment Instructions:
1. Copy this file to: /Users/noahdeskin/conductor/queryable-slack-2/frontend/api/chat-debug.py
2. Deploy: cd frontend && vercel --prod --force
3. Access: https://queryable-slack.vercel.app/api/chat-debug
"""

import sys
import os
import json
import logging
import traceback
from pathlib import Path
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# Configure logging with timestamps
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to Python path for conductor package imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))


class handler(BaseHTTPRequestHandler):
    """Debug handler for /api/chat endpoint issues"""

    def do_GET(self):
        """Handle GET requests - return diagnostic info"""
        logger.info("GET request received at /api/chat-debug")
        diagnostics = self._run_full_diagnostics()
        self.send_json_response(200, diagnostics)

    def do_POST(self):
        """Handle POST requests - log and test the full flow"""
        logger.info("POST request received at /api/chat-debug")
        
        # Read request body with error handling
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            logger.info(f"Content-Length: {content_length}")
            
            if content_length > 0:
                body = self.rfile.read(content_length).decode('utf-8')
                logger.debug(f"Raw request body: {body[:500]}...")
                data = json.loads(body)
            else:
                data = {}
                
        except Exception as e:
            logger.error(f"Failed to read/parse request body: {e}")
            self.send_json_response(400, {
                "error": "Invalid request body",
                "details": str(e),
                "content_length": content_length
            })
            return

        # Log request headers
        self._log_headers()

        # Run comprehensive diagnostics
        diagnostics = self._run_full_diagnostics()
        
        # Test the actual flow
        diagnostics["request_test"] = self._test_request_flow(data)
        
        self.send_json_response(200, diagnostics)

    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        logger.info("OPTIONS request received")
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()

    def _run_full_diagnostics(self) -> dict:
        """Run comprehensive system diagnostics"""
        logger.info("Running full system diagnostics...")
        
        diagnostics = {
            "timestamp": datetime.utcnow().isoformat(),
            "endpoint": "/api/chat-debug",
            "status": "diagnostic_run_complete"
        }

        # 1. Environment Variables Check
        logger.info("Checking environment variables...")
        diagnostics["environment"] = self._check_environment_variables()

        # 2. Python Environment Info
        logger.info("Gathering Python environment info...")
        diagnostics["python_environment"] = self._check_python_environment()

        # 3. Module Imports Test
        logger.info("Testing module imports...")
        diagnostics["module_imports"] = self._test_module_imports()

        # 4. File System Check
        logger.info("Checking file system...")
        diagnostics["filesystem"] = self._check_filesystem()

        # 5. Supabase Connectivity
        logger.info("Testing Supabase connectivity...")
        diagnostics["supabase_connectivity"] = self._test_supabase_connectivity()

        # 6. API Gateway Connectivity
        logger.info("Testing Vercel AI Gateway...")
        diagnostics["api_gateway"] = self._test_api_gateway()

        # 7. Anthropic Connectivity
        logger.info("Testing Anthropic API...")
        diagnostics["anthropic_api"] = self._test_anthropic_api()

        # 8. Vercel Environment
        logger.info("Gathering Vercel environment info...")
        diagnostics["vercel_environment"] = self._check_vercel_environment()

        # 9. Generate Summary
        diagnostics["summary"] = self._generate_diagnostic_summary(diagnostics)

        logger.info(f"Diagnostics complete. Status: {diagnostics['summary']['overall_status']}")
        return diagnostics

    def _check_environment_variables(self) -> dict:
        """Check all required environment variables"""
        logger.info("Checking environment variables...")
        
        required_vars = {
            "ANTHROPIC_API_KEY": "Claude API key",
            "AI_GATEWAY_API_KEY": "Vercel AI Gateway key",
            "SUPABASE_URL": "Supabase project URL",
            "SUPABASE_ANON_KEY": "Supabase anonymous key"
        }

        env_status = {}
        for var_name, description in required_vars.items():
            value = os.getenv(var_name, "")
            is_present = bool(value.strip())
            
            env_status[var_name] = {
                "description": description,
                "present": is_present,
                "length": len(value) if value else 0,
                "first_chars": value[:8] + "..." if is_present else None,
                "last_chars": "..." + value[-4:] if is_present else None
            }
            
            logger.info(f"  {var_name}: {'PRESENT' if is_present else 'MISSING'} (len={len(value)})")

        return env_status

    def _check_python_environment(self) -> dict:
        """Check Python environment"""
        logger.info("Checking Python environment...")
        
        return {
            "python_version": sys.version,
            "executable": sys.executable,
            "prefix": sys.prefix,
            "path_count": len(sys.path),
            "path_sample": sys.path[:3],
            "cwd": os.getcwd(),
            "user": os.getenv("USER", "unknown"),
            "home": os.getenv("HOME", "unknown")
        }

    def _test_module_imports(self) -> dict:
        """Test all critical module imports"""
        logger.info("Testing module imports...")
        
        import_tests = {}

        # Core packages
        core_packages = [
            "http.server",
            "json",
            "logging",
            "pathlib",
            "anthropic",
            "openai",
            "supabase",
            "dotenv",
            "pydantic",
            "httpx"
        ]

        for package_name in core_packages:
            try:
                __import__(package_name)
                import_tests[package_name] = {"status": "OK", "error": None}
                logger.info(f"  {package_name}: OK")
            except Exception as e:
                import_tests[package_name] = {
                    "status": "FAILED",
                    "error": str(e)
                }
                logger.warning(f"  {package_name}: FAILED - {e}")

        # Conductor package imports
        try:
            import conductor
            import_tests["conductor"] = {"status": "OK", "error": None}
            logger.info("  conductor: OK")
        except Exception as e:
            import_tests["conductor"] = {"status": "FAILED", "error": str(e)}
            logger.warning(f"  conductor: FAILED - {e}")

        # Conductor submodules
        submodules = [
            "conductor.supabase_query",
            "conductor.models",
            "conductor.user_mapper"
        ]

        for submodule in submodules:
            try:
                __import__(submodule)
                import_tests[submodule] = {"status": "OK", "error": None}
                logger.info(f"  {submodule}: OK")
            except Exception as e:
                import_tests[submodule] = {"status": "FAILED", "error": str(e)}
                logger.warning(f"  {submodule}: FAILED - {e}")

        # Critical function imports
        critical_functions = [
            ("conductor.supabase_query", "query_vector_similarity"),
            ("anthropic", "Anthropic"),
            ("openai", "OpenAI")
        ]

        for module_name, func_name in critical_functions:
            try:
                module = __import__(module_name, fromlist=[func_name])
                getattr(module, func_name)
                import_tests[f"{module_name}.{func_name}"] = {"status": "OK", "error": None}
                logger.info(f"  {module_name}.{func_name}: OK")
            except Exception as e:
                import_tests[f"{module_name}.{func_name}"] = {
                    "status": "FAILED",
                    "error": str(e)
                }
                logger.warning(f"  {module_name}.{func_name}: FAILED - {e}")

        return import_tests

    def _check_filesystem(self) -> dict:
        """Check file system and package structure"""
        logger.info("Checking file system...")
        
        try:
            api_dir = Path(__file__).parent
            parent_dir = api_dir.parent
            conductor_dir = parent_dir / "conductor"

            conductor_files = []
            if conductor_dir.exists():
                conductor_files = [
                    {"name": f.name, "size": f.stat().st_size if f.is_file() else None}
                    for f in sorted(conductor_dir.iterdir())[:15]
                ]

            return {
                "api_dir": str(api_dir),
                "api_dir_exists": api_dir.exists(),
                "parent_dir": str(parent_dir),
                "parent_dir_exists": parent_dir.exists(),
                "conductor_dir": str(conductor_dir),
                "conductor_dir_exists": conductor_dir.exists(),
                "conductor_files": conductor_files,
                "files_count": len(conductor_files)
            }
        except Exception as e:
            logger.error(f"File system check failed: {e}")
            return {"error": str(e), "traceback": traceback.format_exc()}

    def _test_supabase_connectivity(self) -> dict:
        """Test Supabase connection"""
        logger.info("Testing Supabase connectivity...")
        
        try:
            from supabase import create_client
            
            url = os.getenv("SUPABASE_URL", "").strip()
            key = os.getenv("SUPABASE_ANON_KEY", "").strip()

            if not url or not key:
                logger.warning("Supabase credentials missing")
                return {
                    "status": "FAILED",
                    "reason": "Credentials not configured",
                    "url_present": bool(url),
                    "key_present": bool(key)
                }

            logger.info(f"Creating Supabase client for: {url[:30]}...")
            client = create_client(url, key)

            # Try a simple query
            logger.info("Attempting to query conductor_sessions table...")
            result = client.schema('vecs').from_('conductor_sessions').select('id').limit(1).execute()

            return {
                "status": "OK",
                "url": url[:50] + "...",
                "connected": True,
                "table_accessible": True,
                "sample_query_rows": len(result.data) if result.data else 0
            }

        except Exception as e:
            logger.error(f"Supabase connectivity test failed: {e}")
            return {
                "status": "FAILED",
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()[:500]
            }

    def _test_api_gateway(self) -> dict:
        """Test Vercel AI Gateway connectivity"""
        logger.info("Testing Vercel AI Gateway...")
        
        try:
            from openai import OpenAI
            
            key = os.getenv("AI_GATEWAY_API_KEY", "").strip()

            if not key:
                logger.warning("AI Gateway key not configured")
                return {
                    "status": "FAILED",
                    "reason": "API key not configured"
                }

            logger.info("Creating OpenAI client for AI Gateway...")
            client = OpenAI(
                api_key=key,
                base_url="https://ai-gateway.vercel.sh/v1"
            )

            # Test with a simple embedding request (minimal cost)
            logger.info("Testing embedding request...")
            response = client.embeddings.create(
                model="openai/text-embedding-3-small",
                input="test query",
                dimensions=384,
                encoding_format="float"
            )

            return {
                "status": "OK",
                "gateway_url": "https://ai-gateway.vercel.sh/v1",
                "model": "openai/text-embedding-3-small",
                "dimensions": 384,
                "embedding_received": len(response.data[0].embedding) if response.data else 0
            }

        except Exception as e:
            logger.error(f"AI Gateway test failed: {e}")
            return {
                "status": "FAILED",
                "error": str(e),
                "error_type": type(e).__name__,
                "gateway_url": "https://ai-gateway.vercel.sh/v1"
            }

    def _test_anthropic_api(self) -> dict:
        """Test Anthropic API connectivity"""
        logger.info("Testing Anthropic API...")
        
        try:
            from anthropic import Anthropic
            
            key = os.getenv("ANTHROPIC_API_KEY", "").strip()

            if not key:
                logger.warning("Anthropic key not configured")
                return {
                    "status": "FAILED",
                    "reason": "API key not configured"
                }

            logger.info("Creating Anthropic client...")
            client = Anthropic(api_key=key)

            # Test with a simple message (note: this will use tokens)
            logger.info("Testing message creation...")
            message = client.messages.create(
                model="claude-opus-4-1-20250805",
                max_tokens=10,
                messages=[
                    {
                        "role": "user",
                        "content": "test"
                    }
                ]
            )

            return {
                "status": "OK",
                "model": "claude-opus-4-1-20250805",
                "message_created": True,
                "stop_reason": message.stop_reason if hasattr(message, 'stop_reason') else "unknown"
            }

        except Exception as e:
            logger.error(f"Anthropic API test failed: {e}")
            return {
                "status": "FAILED",
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _check_vercel_environment(self) -> dict:
        """Check Vercel deployment environment"""
        logger.info("Checking Vercel environment...")
        
        return {
            "is_vercel": bool(os.getenv("VERCEL")),
            "vercel_env": os.getenv("VERCEL_ENV"),
            "vercel_region": os.getenv("VERCEL_REGION"),
            "vercel_url": os.getenv("VERCEL_URL"),
            "node_env": os.getenv("NODE_ENV"),
            "build_id": os.getenv("VERCEL_BUILD_ID")
        }

    def _test_request_flow(self, data: dict) -> dict:
        """Test the full request flow for /api/chat"""
        logger.info(f"Testing request flow with data keys: {list(data.keys())}")
        
        test_result = {
            "request_received": True,
            "request_keys": list(data.keys()),
            "steps": []
        }

        # Step 1: Check query parameter
        query = data.get('query', '')
        step1 = {
            "step": 1,
            "name": "Extract query parameter",
            "status": "OK" if query else "FAILED",
            "query_present": bool(query),
            "query_length": len(query)
        }
        test_result["steps"].append(step1)
        logger.info(f"Step 1: {step1['status']}")

        # Step 2: Try to generate embedding
        step2 = {
            "step": 2,
            "name": "Generate embedding via AI Gateway",
            "status": "NOT_RUN",
            "embedding_length": 0
        }

        if query:
            try:
                from openai import OpenAI
                
                key = os.getenv("AI_GATEWAY_API_KEY", "").strip()
                if key:
                    logger.info("Step 2: Creating OpenAI client...")
                    client = OpenAI(
                        api_key=key,
                        base_url="https://ai-gateway.vercel.sh/v1"
                    )

                    logger.info(f"Step 2: Requesting embedding for: {query[:50]}...")
                    response = client.embeddings.create(
                        model="openai/text-embedding-3-small",
                        input=query,
                        dimensions=384,
                        encoding_format="float"
                    )

                    step2["status"] = "OK"
                    step2["embedding_length"] = len(response.data[0].embedding)
                    logger.info(f"Step 2: Embedding generated (length={step2['embedding_length']})")
                else:
                    step2["status"] = "FAILED"
                    step2["reason"] = "AI Gateway key not configured"
                    logger.warning("Step 2: AI Gateway key missing")

            except Exception as e:
                step2["status"] = "FAILED"
                step2["error"] = str(e)
                step2["error_type"] = type(e).__name__
                logger.error(f"Step 2: Embedding generation failed - {e}")

        test_result["steps"].append(step2)

        # Step 3: Try to query Supabase
        step3 = {
            "step": 3,
            "name": "Query Supabase vector similarity",
            "status": "NOT_RUN"
        }

        if step2["status"] == "OK" and step2.get("embedding_length", 0) > 0:
            try:
                from conductor.supabase_query import query_vector_similarity
                
                logger.info("Step 3: Calling query_vector_similarity...")
                embedding = [0.1] * 384  # Use dummy embedding for testing
                
                results = query_vector_similarity(
                    query_embedding=embedding,
                    match_threshold=0.0,
                    match_count=3
                )

                step3["status"] = "OK"
                step3["results_found"] = len(results.get('ids', [[]])[0])
                logger.info(f"Step 3: Vector search returned {step3['results_found']} results")

            except Exception as e:
                step3["status"] = "FAILED"
                step3["error"] = str(e)
                step3["error_type"] = type(e).__name__
                logger.error(f"Step 3: Vector search failed - {e}")

        test_result["steps"].append(step3)

        # Step 4: Try to call Claude
        step4 = {
            "step": 4,
            "name": "Generate response with Claude",
            "status": "NOT_RUN"
        }

        if step3["status"] == "OK":
            try:
                from anthropic import Anthropic
                
                key = os.getenv("ANTHROPIC_API_KEY", "").strip()
                if key:
                    logger.info("Step 4: Creating Anthropic client...")
                    client = Anthropic(api_key=key)

                    logger.info("Step 4: Sending test message to Claude...")
                    message = client.messages.create(
                        model="claude-opus-4-1-20250805",
                        max_tokens=50,
                        messages=[
                            {
                                "role": "user",
                                "content": "Acknowledge this is a test."
                            }
                        ]
                    )

                    step4["status"] = "OK"
                    step4["response_received"] = True
                    logger.info("Step 4: Response from Claude received")

                else:
                    step4["status"] = "FAILED"
                    step4["reason"] = "Anthropic key not configured"
                    logger.warning("Step 4: Anthropic key missing")

            except Exception as e:
                step4["status"] = "FAILED"
                step4["error"] = str(e)
                step4["error_type"] = type(e).__name__
                logger.error(f"Step 4: Claude call failed - {e}")

        test_result["steps"].append(step4)

        return test_result

    def _generate_diagnostic_summary(self, diagnostics: dict) -> dict:
        """Generate a summary of diagnostic findings"""
        logger.info("Generating diagnostic summary...")
        
        issues = []
        
        # Check environment variables
        env = diagnostics.get("environment", {})
        for var_name, info in env.items():
            if not info.get("present"):
                issues.append(f"CRITICAL: {var_name} not configured")

        # Check critical imports
        imports = diagnostics.get("module_imports", {})
        critical_imports = [
            "anthropic",
            "openai",
            "supabase",
            "conductor.supabase_query"
        ]
        
        for imp in critical_imports:
            if imports.get(imp, {}).get("status") == "FAILED":
                issues.append(f"CRITICAL: {imp} import failed")

        # Check Supabase
        supabase = diagnostics.get("supabase_connectivity", {})
        if supabase.get("status") == "FAILED":
            issues.append(f"ERROR: Supabase connection failed - {supabase.get('reason', supabase.get('error', 'unknown'))}")

        # Check API Gateway
        gateway = diagnostics.get("api_gateway", {})
        if gateway.get("status") == "FAILED":
            issues.append(f"ERROR: AI Gateway connection failed")

        # Check Anthropic
        anthropic = diagnostics.get("anthropic_api", {})
        if anthropic.get("status") == "FAILED":
            issues.append(f"ERROR: Anthropic API connection failed")

        overall_status = "HEALTHY" if not issues else ("DEGRADED" if len(issues) < 3 else "UNHEALTHY")

        summary = {
            "overall_status": overall_status,
            "total_issues": len(issues),
            "issues": issues if issues else ["All systems operational"],
            "next_steps": self._get_next_steps(issues)
        }

        logger.info(f"Diagnostic summary: {overall_status} ({len(issues)} issues)")
        return summary

    def _get_next_steps(self, issues: list) -> list:
        """Provide actionable next steps based on issues"""
        logger.info(f"Generating next steps for {len(issues)} issues...")
        
        if not issues:
            return [
                "1. System is fully operational",
                "2. Test the /api/chat endpoint with a query",
                "3. Monitor Vercel logs for runtime errors",
                "4. Check frontend console for errors"
            ]

        steps = []

        # Environment issues
        env_issues = [i for i in issues if "not configured" in i]
        if env_issues:
            steps.append("FIX ENVIRONMENT VARIABLES:")
            for issue in env_issues:
                var = issue.split(": ")[1]
                steps.append(f"  1. vercel env add {var} production")
            steps.append("  2. vercel --prod --force")

        # Import issues
        import_issues = [i for i in issues if "import failed" in i]
        if import_issues:
            steps.append("")
            steps.append("FIX IMPORT ERRORS:")
            steps.append("  1. Check requirements.txt for all dependencies")
            steps.append("  2. Verify conductor package structure")
            steps.append("  3. Run: vercel --prod --force")

        # Connection issues
        connection_issues = [i for i in issues if "connection failed" in i or "Connection failed" in i]
        if connection_issues:
            steps.append("")
            steps.append("CHECK CONNECTIONS:")
            steps.append("  1. Verify Supabase project is active")
            steps.append("  2. Verify API Gateway credentials")
            steps.append("  3. Verify Anthropic API key is valid")
            steps.append("  4. Check network connectivity from Vercel")

        steps.append("")
        steps.append("DEBUG:")
        steps.append("  1. View full diagnostics: GET /api/chat-debug")
        steps.append("  2. Check Vercel logs: vercel logs --follow")
        steps.append("  3. Test endpoint: curl -X POST https://queryable-slack.vercel.app/api/chat-debug -d '{\"query\":\"test\"}'")

        return steps

    def _log_headers(self):
        """Log all request headers for debugging"""
        logger.info("Request headers:")
        for header_name, header_value in self.headers.items():
            # Mask sensitive headers
            if any(sensitive in header_name.lower() for sensitive in ['auth', 'key', 'token']):
                logger.debug(f"  {header_name}: ***MASKED***")
            else:
                logger.debug(f"  {header_name}: {header_value}")

    def send_json_response(self, status_code: int, data: dict):
        """Send JSON response with CORS headers"""
        logger.info(f"Sending response: status={status_code}, keys={list(data.keys())}")
        
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        response_body = json.dumps(data, indent=2)
        self.wfile.write(response_body.encode())
        logger.debug(f"Response body length: {len(response_body)}")
